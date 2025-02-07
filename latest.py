#!/usr/bin/env python3

import sys
import threading
import time
import queue
import subprocess
from typing import Optional, List, Tuple
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                            QTextEdit, QLineEdit, QSpinBox, QCheckBox, 
                            QGroupBox, QFrame, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

class NFCReaderGUI(QMainWindow):
    # APDU Commands
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    READ_PAGE = [0xFF, 0xB0, 0x00]  # Will append page number and length
    LOCK_CARD = [0xFF, 0xD6, 0x00, 0x02, 0x04, 0x00, 0x00, 0x00, 0x00]

    # Signals for thread-safe GUI updates
    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str, str)
    write_status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    url_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NFC Reader/Writer")
        self.setMinimumSize(900, 700)
        
        # Initialize reader
        try:
            from smartcard.System import readers
            from smartcard.util import toHexString
            from smartcard.Exceptions import NoReadersException
            self.readers = readers
            self.toHexString = toHexString
        except ImportError:
            QMessageBox.critical(self, "Error", "pyscard not installed. Please install required packages.")
            sys.exit(1)

        # Initialize variables
        self.scanning = False
        self.scan_thread = None
        self.tag_queue = queue.Queue()
        self.last_connection_time = 0
        self.reader = None

        # Setup UI
        self.setup_ui()
        
        # Connect signals
        self.status_signal.connect(self.update_status_label)
        self.log_signal.connect(self.append_log)
        self.write_status_signal.connect(self.update_write_status)
        self.progress_signal.connect(self.update_progress)
        self.url_signal.connect(self.update_url_label)
        
        # Start checking for reader
        self.check_reader_timer = QTimer()
        self.check_reader_timer.timeout.connect(self.check_reader)
        self.check_reader_timer.start(2000)
        
        # Setup queue check timer
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.check_tag_queue)
        self.queue_timer.start(100)

        # Apply dark theme
        self.apply_dark_theme()

    def apply_dark_theme(self):
        """Apply dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #3a3a3a;
                color: #ffffff;
                padding: 8px 20px;
                border: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a4a4a;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #0d47a1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0a3d91;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 4px;
            }
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px;
            }
            QSpinBox {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                padding: 6px;
            }
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                margin-top: 1em;
                padding-top: 1em;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #3a3a3a;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0d47a1;
                background-color: #0d47a1;
            }
        """)

    def setup_ui(self):
        """Setup the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.read_tab = QWidget()
        self.write_tab = QWidget()
        self.tab_widget.addTab(self.read_tab, "Read Tags")
        self.tab_widget.addTab(self.write_tab, "Write Tags")
        
        # Setup read interface
        self.setup_read_interface()
        
        # Setup write interface
        self.setup_write_interface()

    def setup_read_interface(self):
        """Setup the read tab interface."""
        layout = QVBoxLayout(self.read_tab)
        
        # Status section
        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        self.status_label = QLabel("Status: Waiting for reader...")
        self.status_label.setStyleSheet("color: #ffd700;")  # Golden yellow for status
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_frame)
        
        # Scan button
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.clicked.connect(self.toggle_scanning)
        self.scan_button.setFixedWidth(200)
        layout.addWidget(self.scan_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # URL Detection group
        url_group = QGroupBox("Detected URL")
        url_layout = QHBoxLayout(url_group)
        self.url_label = QLabel("")
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.copy_url_button = QPushButton()
        self.copy_url_button.setIcon(QIcon.fromTheme("edit-copy"))
        self.copy_url_button.setToolTip("Copy URL to clipboard")
        self.copy_url_button.clicked.connect(self.copy_detected_url)
        self.copy_url_button.setFixedSize(30, 30)
        url_layout.addWidget(self.url_label)
        url_layout.addWidget(self.copy_url_button)
        layout.addWidget(url_group)
        
        # Log group
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 10))
        log_layout.addWidget(self.log_text)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Copy and Clear buttons
        self.copy_button = QPushButton("Copy Log")
        self.copy_button.clicked.connect(self.copy_log)
        self.clear_button = QPushButton("Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        log_layout.addWidget(button_container)
        layout.addWidget(log_group)

    def setup_write_interface(self):
        """Setup the write tab interface."""
        layout = QVBoxLayout(self.write_tab)
        
        # Input section
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout(input_group)
        
        # URL/Text input
        input_label = QLabel("Enter URL or text to write:")
        input_label.setFont(QFont("", 10, QFont.Weight.Bold))
        self.write_entry = QLineEdit()
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.write_entry)
        
        # Batch writing section
        batch_widget = QWidget()
        batch_layout = QHBoxLayout(batch_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        
        quantity_label = QLabel("Number of tags to write:")
        self.quantity_spinbox = QSpinBox()
        self.quantity_spinbox.setRange(1, 100)
        self.quantity_spinbox.setValue(1)
        
        batch_layout.addWidget(quantity_label)
        batch_layout.addWidget(self.quantity_spinbox)
        batch_layout.addStretch()
        
        input_layout.addWidget(batch_widget)
        layout.addWidget(input_group)
        
        # Options section
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout(options_group)
        
        self.lock_checkbox = QCheckBox("Lock tag after writing")
        self.lock_checkbox.setChecked(True)
        options_layout.addWidget(self.lock_checkbox)
        
        self.write_button = QPushButton("Write to Tag")
        self.write_button.clicked.connect(self.write_tag)
        self.write_button.setFixedWidth(200)
        options_layout.addWidget(self.write_button)
        options_layout.addStretch()
        
        layout.addWidget(options_group)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress_label = QLabel("")
        progress_layout.addWidget(self.progress_label)
        layout.addWidget(progress_group)
        
        # Status section
        status_group = QGroupBox("Status")
        status_layout = QHBoxLayout(status_group)
        self.write_status = QLabel("")
        status_layout.addWidget(self.write_status)
        
        self.clear_status_button = QPushButton("Clear Status")
        self.clear_status_button.clicked.connect(lambda: self.write_status.setText(""))
        status_layout.addWidget(self.clear_status_button)
        
        layout.addWidget(status_group)
        layout.addStretch()

    def check_reader(self):
        """Check for ACR1252U reader and update status."""
        try:
            available_readers = self.readers()
            self.reader = None
            
            for r in available_readers:
                if "ACR1252" in str(r):
                    self.reader = r
                    self.status_signal.emit("Status: Reader connected")
                    return

            self.status_signal.emit("Status: ACR1252U not found")
        except Exception as e:
            self.status_signal.emit(f"Status: Error - {str(e)}")

    def connect_with_retry(self) -> Tuple[any, bool]:
        """Try to connect to the card with retries."""
        current_time = time.time()
        if current_time - self.last_connection_time < 0.2:
            return None, False
            
        self.last_connection_time = current_time
        connection = self.reader.createConnection()
        
        for attempt in range(3):
            for protocol in ['T1', 'T0', None]:
                try:
                    if protocol:
                        connection.connect(cardProtocol=protocol)
                    else:
                        connection.connect()
                    return connection, True
                except:
                    time.sleep(0.1 * (attempt + 1))
        
        return None, False

    def read_tag_memory(self, connection) -> List[int]:
        """Read NTAG213 memory pages."""
        all_data = []
        # NTAG213 has pages 4-39 available for user data
        for page in range(4, 40):  # Read all available user pages
            try:
                read_cmd = self.READ_PAGE + [page, 0x04]  # Read 4 bytes
                response, sw1, sw2 = connection.transmit(read_cmd)
                if sw1 == 0x90:
                    all_data.extend(response)
                    self.log_signal.emit("Debug", f"Page {page}: {self.toHexString(response)}")
                else:
                    break  # Stop if we hit an error or end of memory
            except:
                break
        return all_data

    def on_tab_changed(self, index):
        """Handle tab change events."""
        if index == 1 and self.scanning:  # Index 1 is Write Tags tab
            self.toggle_scanning()  # Stop scanning when switching to write tab
            
    def toggle_scanning(self):
        """Toggle the scanning process."""
        if not self.scanning:
            self.scanning = True
            self.scan_button.setText("Stop Scanning")
            self.scan_button.setStyleSheet("background-color: #c62828;")  # Red for stop
            self.log_signal.emit("System", "Started scanning for tags")
            self.scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
            self.scan_thread.start()
        else:
            self.scanning = False
            self.scan_button.setText("Start Scanning")
            self.scan_button.setStyleSheet("")  # Reset to default style
            self.log_signal.emit("System", "Stopped scanning")

    def scan_loop(self):
        """Continuous scanning loop."""
        last_uid = None
        
        while self.scanning:
            try:
                if self.reader:
                    connection, connected = self.connect_with_retry()
                    if not connected:
                        time.sleep(0.2)
                        continue
                        
                    # Get UID
                    response, sw1, sw2 = connection.transmit(self.GET_UID)
                    if sw1 == 0x90:
                        uid = self.toHexString(response)
                        
                        # Only process if it's a new tag
                        if uid != last_uid:
                            last_uid = uid
                            self.log_signal.emit("New tag detected", f"UID: {uid}")
                            
                            # Read tag memory
                            memory_data = self.read_tag_memory(connection)
                            if memory_data:
                                self.process_ndef_content(memory_data)
                    
                    connection.disconnect()
            except Exception as e:
                error_msg = str(e)
                # Only log errors that aren't common disconnection messages
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]):
                    self.log_signal.emit("Error", f"Scan error: {error_msg}")
                last_uid = None  # Reset UID on error
                
            time.sleep(0.2)  # Delay between scans

    def process_ndef_content(self, data: List[int]):
        """Process NDEF content and open URLs if found."""
        try:
            self.log_signal.emit("Debug", f"Raw data: {self.toHexString(data)}")
            
            if len(data) < 4:  # Need at least TLV header
                self.log_signal.emit("Debug", f"Data too short for NDEF: {len(data)} bytes")
                return
                
            # Check for TLV structure
            current_pos = 0
            while current_pos < len(data):
                tlv_type = data[current_pos]
                if tlv_type == 0xFE:  # Terminator TLV
                    break
                    
                # Get length for TLV types that have a length field
                if tlv_type in [0x01, 0x02, 0x03]:
                    length = data[current_pos + 1]
                    current_pos += 2  # Skip type and length bytes
                else:
                    current_pos += 1
                    continue
                
                # Process NDEF message (type 0x03) or Capability Container (type 0x01)
                if tlv_type == 0x03 or (tlv_type == 0x01 and length > 0):  # NDEF TLV or CC
                    self.log_signal.emit("Debug", f"TLV type 0x{tlv_type:02X} found, length: {length} bytes")
                    self.log_signal.emit("Debug", f"Total data available: {len(data)} bytes")
                    
                    # Skip CC and look for NDEF message if this is a CC TLV
                    if tlv_type == 0x01:
                        current_pos += length
                        continue
                        
                    try:
                        # Parse NDEF record header
                        flags = data[current_pos]  # Record header flags
                        tnf = flags & 0x07  # Type Name Format (last 3 bits)
                        is_first = (flags & 0x80) != 0  # MB (Message Begin)
                        is_last = (flags & 0x40) != 0   # ME (Message End)
                        cf_flag = (flags & 0x20) != 0   # CF (Chunk Flag)
                        sr_flag = (flags & 0x10) != 0   # SR (Short Record)
                        il_flag = (flags & 0x08) != 0   # IL (ID Length present)
                        
                        type_length = data[current_pos + 1]  # Length of the type field
                        payload_length = data[current_pos + 2]  # Length of the payload
                        record_type = data[current_pos + 3:current_pos + 3 + type_length]  # Type field
                        
                        self.log_signal.emit("Debug", f"Record flags: MB={is_first}, ME={is_last}, CF={cf_flag}, SR={sr_flag}, IL={il_flag}, TNF={tnf}")
                        self.log_signal.emit("Debug", f"Type length: {type_length}")
                        self.log_signal.emit("Debug", f"Payload length: {payload_length}")
                        self.log_signal.emit("Debug", f"Record type: {self.toHexString(record_type)}")
                        self.log_signal.emit("Debug", f"Record type as bytes: {bytes(record_type)}")
                        
                        # Calculate payload offset based on flags
                        offset = current_pos + 3 + type_length  # Skip header and type
                        if il_flag:
                            id_length = data[offset]
                            offset += 1 + id_length  # Skip ID length and ID field
                        
                        # Check record type (both as bytes and as ASCII)
                        record_type_bytes = bytes(record_type)
                        if record_type_bytes == b'U' or (len(record_type) == 1 and record_type[0] == 0x55):  # URL Record
                            # Debug raw data around the URL
                            self.log_signal.emit("Debug", f"Raw data at offset: {self.toHexString(data[offset:offset+payload_length])}")
                            
                            url_prefix_byte = data[offset]  # First byte of payload is URL prefix
                            content_bytes = data[offset+1:offset+payload_length]  # Rest is URL
                            
                            # Debug the raw URL prefix byte
                            self.log_signal.emit("Debug", f"URL prefix byte: 0x{url_prefix_byte:02X}")
                            
                            # URL prefixes according to NFC Forum URI Record Type Definition
                            url_prefixes = {
                                0x00: "http://www.",
                                0x01: "https://www.",
                                0x02: "http://",
                                0x03: "https://",
                                0x04: "tel:",
                                0x05: "mailto:",
                                0x06: "ftp://anonymous:anonymous@",
                                0x07: "ftp://ftp.",
                                0x08: "ftps://",
                                0x09: "sftp://",
                                0x0A: "smb://",
                                0x0B: "nfs://",
                                0x0C: "ftp://",
                                0x0D: "dav://",
                                0x0E: "news:",
                                0x0F: "telnet://",
                                0x10: "imap:",
                                0x11: "rtsp://",
                                0x12: "urn:",
                                0x13: "pop:",
                                0x14: "sip:",
                                0x15: "sips:",
                                0x16: "tftp:",
                                0x17: "btspp://",
                                0x18: "btl2cap://",
                                0x19: "btgoep://",
                                0x1A: "tcpobex://",
                                0x1B: "irdaobex://",
                                0x1C: "file://",
                                0x1D: "urn:epc:id:",
                                0x1E: "urn:epc:tag:",
                                0x1F: "urn:epc:pat:",
                                0x20: "urn:epc:raw:",
                                0x21: "urn:epc:",
                                0x22: "urn:nfc:",
                            }
                            
                            # Get the URL content first
                            url_content = bytes(content_bytes).decode('utf-8')
                            self.log_signal.emit("Debug", f"URL content before prefix: {url_content}")
                            
                            # Detect if the content looks like a web URL despite the prefix
                            looks_like_web = any(
                                url_content.startswith(domain_part) for domain_part in [
                                    "www.", 
                                    "http", # Will match http:// or https://
                                    # Common domain patterns
                                    "github.com",
                                    "gitlab.com",
                                    "bitbucket.org",
                                    "homebox.",
                                    "box.",
                                    "docs.",
                                    "drive."
                                ]
                            ) or any(
                                "." + tld in url_content.lower() for tld in [
                                    "com",
                                    "org",
                                    "net",
                                    "edu",
                                    "gov",
                                    "io",
                                    "app"
                                ]
                            )
                            
                            # Get prefix from byte, but override if content looks like a web URL
                            original_prefix = url_prefixes.get(url_prefix_byte, "")
                            if looks_like_web and original_prefix in ["tel:", "mailto:"]:
                                self.log_signal.emit("Debug", f"Overriding {original_prefix} prefix with http:// for web-like URL")
                                prefix = "http://"
                            else:
                                prefix = original_prefix
                                if prefix:
                                    self.log_signal.emit("Debug", f"Using original prefix: {prefix}")
                                else:
                                    self.log_signal.emit("Debug", f"Unknown URL prefix byte: 0x{url_prefix_byte:02X}")
                            
                            # Construct full URL
                            url = prefix + url_content
                            
                            # Additional validation for tel: URLs
                            if url.startswith("tel:") and not url_content.replace("+","").replace("-","").replace(".","").isdigit():
                                self.log_signal.emit("Debug", "Converting invalid tel: URL to http://")
                                url = "http://" + url_content
                            self.log_signal.emit("Debug", f"URL prefix: {prefix}")
                            self.log_signal.emit("Debug", f"URL content: {bytes(content_bytes).decode('utf-8')}")
                            self.log_signal.emit("URL Detected", f"Complete URL: {url}")
                            self.url_signal.emit(url)
                            
                            # Only try to open web URLs (not tel: or mailto:)
                            if url.startswith(("http://", "https://")):
                                # Try to open URL with different methods
                                methods = [
                                    (['xdg-open', url], "System default browser"),
                                    (['firefox', url], "Firefox"),
                                    (['google-chrome', url], "Chrome"),
                                    (['chromium', url], "Chromium"),
                                    (['sensible-browser', url], "Default browser (Debian/Ubuntu)"),
                                ]
                                
                                success = False
                                for cmd, method in methods:
                                    try:
                                        self.log_signal.emit("Browser", f"Attempting to open URL with {method}")
                                        # Use start_new_session=True to detach browser from this process
                                        result = subprocess.run(
                                            cmd, 
                                            capture_output=True, 
                                            text=True,
                                            start_new_session=True
                                        )
                                        if result.returncode == 0:
                                            self.log_signal.emit("Browser", f"Successfully opened URL with {method}")
                                            success = True
                                            break
                                        else:
                                            self.log_signal.emit("Debug", f"{method} failed: {result.stderr}")
                                    except FileNotFoundError:
                                        self.log_signal.emit("Debug", f"{method} not found, trying next method")
                                        continue
                                    except Exception as e:
                                        self.log_signal.emit("Debug", f"{method} error: {str(e)}")
                                        continue
                                
                                if not success:
                                    self.log_signal.emit("Error", "Failed to open URL with any available browser")
                        elif record_type_bytes == b'T' or (len(record_type) == 1 and record_type[0] == 0x54):  # Text Record
                            # First byte contains text info
                            text_info = data[offset]
                            lang_code_length = text_info & 0x3F  # Lower 6 bits
                            content_start = offset + 1 + lang_code_length
                            content_bytes = data[content_start:content_start+payload_length-1-lang_code_length]  # -1 for status byte
                            
                            # Show language code if present
                            if lang_code_length > 0:
                                lang_code = bytes(data[offset+1:offset+1+lang_code_length]).decode('utf-8')
                                self.log_signal.emit("Debug", f"Language code: {lang_code}")
                            
                            text = bytes(content_bytes).decode('utf-8')
                            self.log_signal.emit("Text Record", f"Content: {text}")
                        else:
                            self.log_signal.emit("Debug", f"Unknown record type: {bytes(record_type)}")
                    except Exception as e:
                        self.log_signal.emit("Error", f"Failed to decode NDEF: {str(e)}")
            else:
                self.log_signal.emit("Debug", f"Not an NDEF TLV (expected 0x03, got 0x{data[0]:02X})")
        except Exception as e:
            self.log_signal.emit("Error", f"Error parsing NDEF: {str(e)}")

    @pyqtSlot()
    def check_tag_queue(self):
        """Check for new tag data and update the GUI."""
        try:
            while True:
                title, message = self.tag_queue.get_nowait()
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                self.log_text.append(f"[{timestamp}] [{title}] {message}")
        except queue.Empty:
            pass

    def copy_detected_url(self):
        """Copy detected URL to clipboard."""
        url = self.url_label.text()
        if url:
            QApplication.clipboard().setText(url)
            self.log_signal.emit("System", "URL copied to clipboard")
    
    def copy_log(self):
        """Copy log content to clipboard."""
        content = self.log_text.toPlainText()
        QApplication.clipboard().setText(content)
        self.log_signal.emit("System", "Log content copied to clipboard")

    def clear_log(self):
        """Clear the log text."""
        self.log_text.clear()
        self.log_signal.emit("System", "Log cleared")

    @pyqtSlot(str)
    def update_status_label(self, text):
        """Update the status label."""
        self.status_label.setText(text)

    @pyqtSlot(str, str)
    def append_log(self, title, message):
        """Append message to log."""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] [{title}] {message}")
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    @pyqtSlot(str)
    def update_write_status(self, text):
        """Update the write status label."""
        self.write_status.setText(text)

    @pyqtSlot(str)
    def update_progress(self, text):
        """Update the progress label."""
        self.progress_label.setText(text)
        
    @pyqtSlot(str)
    def update_url_label(self, text):
        """Update the URL label."""
        self.url_label.setText(text)

    def write_tag(self):
        """Write data to multiple tags."""
        if not self.reader:
            QMessageBox.critical(self, "Error", "Reader not connected")
            return

        text = self.write_entry.text().strip()
        if not text:
            QMessageBox.critical(self, "Error", "Please enter text to write")
            return
            
        quantity = self.quantity_spinbox.value()
        if quantity < 1:
            QMessageBox.critical(self, "Error", "Quantity must be at least 1")
            return
            
        self.write_status.setText("Waiting for tags...")
        self.progress_label.setText(f"Starting batch write: 0/{quantity} tags written")
        
        threading.Thread(target=self.batch_write_tags, 
                       args=(text, quantity), 
                       daemon=True).start()

    def batch_write_tags(self, text: str, quantity: int):
        """Write the same data to multiple tags."""
        tags_written = 0
        last_uid = None
        
        while tags_written < quantity:
            try:
                connection, connected = self.connect_with_retry()
                if not connected:
                    time.sleep(0.2)
                    continue
                    
                # Get UID to check if it's a new tag
                response, sw1, sw2 = connection.transmit(self.GET_UID)
                if sw1 == 0x90:
                    uid = self.toHexString(response)
                    if uid != last_uid:  # Only write to new tags
                        last_uid = uid
                        self.write_status_signal.emit(f"Writing to tag {uid}...")
                        
                        # Write the data
                        text_bytes = list(text.encode('utf-8'))
            
                        # Create NDEF message for NTAG213
                        # Check if it's a URL and determine prefix
                        url_prefixes = {
                            'http://www.': 0x00,
                            'https://www.': 0x01,
                            'http://': 0x02,
                            'https://': 0x03,
                            'tel:': 0x04,
                            'mailto:': 0x05,
                        }
                        
                        prefix_found = None
                        remaining_text = text
                        
                        # Detect if the text looks like a web URL
                        looks_like_web = any(
                            "." + tld in text.lower() for tld in [
                                "com",
                                "org",
                                "net",
                                "edu",
                                "gov",
                                "io",
                                "app"
                            ]
                        )
                        
                        # Determine record type and data
                        if text.startswith(('http://www.', 'https://www.', 'http://', 'https://')):
                            # This is a web URL with explicit prefix
                            for prefix, code in url_prefixes.items():
                                if text.startswith(prefix):
                                    prefix_found = code
                                    remaining_text = text[len(prefix):]
                                    break
                            if prefix_found is not None:
                                # URL record with prefix
                                remaining_bytes = list(remaining_text.encode('utf-8'))
                                ndef_header = [0xD1, 0x01, len(remaining_bytes) + 1] + [0x55]  # Type: U (URL)
                                record_data = [prefix_found] + remaining_bytes
                            else:
                                # Fallback to text if no prefix matched
                                ndef_header = [0xD1, 0x01, len(text_bytes) + 1] + [0x54] + [0x00]  # Type: T (Text)
                                record_data = text_bytes
                        elif looks_like_web:
                            # This looks like a web URL without explicit prefix, add http://
                            prefix_found = 0x02  # http://
                            remaining_bytes = list(text.encode('utf-8'))
                            ndef_header = [0xD1, 0x01, len(remaining_bytes) + 1] + [0x55]  # Type: U (URL)
                            record_data = [prefix_found] + remaining_bytes
                        else:
                            # Store as plain text (including tel: and mailto: URLs)
                            ndef_header = [0xD1, 0x01, len(text_bytes) + 1] + [0x54] + [0x00]  # Type: T (Text)
                            record_data = text_bytes
                        
                        # Calculate total length including headers
                        total_length = len(ndef_header) + len(record_data)
                        
                        # TLV format: 0x03 (NDEF) + length + NDEF message + 0xFE (terminator)
                        ndef_data = [0x03, total_length] + ndef_header + record_data + [0xFE]
                        
                        # Initialize NDEF capability
                        init_command = [0xFF, 0xD6, 0x00, 0x03, 0x04, 0xE1, 0x10, 0x06, 0x0F]
                        response, sw1, sw2 = connection.transmit(init_command)
                        if sw1 != 0x90:
                            raise Exception(f"NDEF initialization failed: {sw1:02X} {sw2:02X}")
                        
                        # Write data in chunks of 4 bytes (one page at a time)
                        chunk_size = 4
                        for i in range(0, len(ndef_data), chunk_size):
                            chunk = ndef_data[i:i + chunk_size]
                            page = 4 + (i // chunk_size)  # Start from page 4
                            
                            # Pad the last chunk with zeros if needed
                            if len(chunk) < chunk_size:
                                chunk = chunk + [0] * (chunk_size - len(chunk))
                            
                            write_command = [0xFF, 0xD6, 0x00, page, chunk_size] + chunk
                            response, sw1, sw2 = connection.transmit(write_command)
                            
                            if sw1 != 0x90:
                                raise Exception(f"Failed to write page {page}")

                        # Lock the tag if requested
                        if self.lock_checkbox.isChecked():
                            response, sw1, sw2 = connection.transmit(self.LOCK_CARD)
                            if sw1 != 0x90:
                                raise Exception("Failed to lock tag")
                        
                        tags_written += 1
                        self.progress_signal.emit(
                            f"Progress: {tags_written}/{quantity} tags written")
                        
                        if tags_written == quantity:
                            self.write_status_signal.emit(
                                f"Successfully wrote {quantity} tags")
                            break
                        else:
                            self.write_status_signal.emit(
                                f"Wrote tag {tags_written}/{quantity}. Please present next tag.")
                
                connection.disconnect()
                
            except Exception as e:
                error_msg = str(e)
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]):
                    self.write_status_signal.emit(f"Error: {error_msg}")
                
            time.sleep(0.2)

def main():
    app = QApplication(sys.argv)
    window = NFCReaderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
