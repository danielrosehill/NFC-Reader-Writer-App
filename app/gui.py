"""
Main GUI class for the NFC Reader/Writer application.
"""

import sys
import threading
import time
import queue
import urllib.request
from typing import Optional, List, Tuple

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
                            QMessageBox, QApplication, QLabel, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QByteArray, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QPixmap, QKeySequence, QShortcut, QColor, QPalette

from app.ui.read_tab import ReadTab
from app.ui.write_tab import WriteTab
from app.ui.copy_tab import CopyTab
from app.ui.about_tab import AboutTab
from app.reader import NFCReader
from app.writer import NFCWriter
from app.copier import NFCCopier
from app.utils import extract_url_from_data, open_url_in_browser, validate_url

class NFCReaderGUI(QMainWindow):
    """Main GUI class for the NFC Reader/Writer application."""
    
    # Signals for thread-safe GUI updates
    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str, str)
    write_status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    progress_value_signal = pyqtSignal(int, int)  # current, total
    url_signal = pyqtSignal(str)
    
    def __init__(self):
        """Initialize the main application window."""
        super().__init__()
        self.setWindowTitle("NFC Reader/Writer v3.6")
        
        # Initialize theme state
        self.dark_mode = False
        
        # Get status bar reference
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
        
        # Initialize reader
        try:
            from smartcard.System import readers
            from smartcard.util import toHexString
            from smartcard.Exceptions import NoReadersException
            self.readers_func = readers
            self.toHexString = toHexString
            
            # Verify reader availability immediately
            self.available_readers = self.readers_func()
            if not self.available_readers:
                QMessageBox.warning(self, "Warning", "No NFC readers found. Please connect a reader and restart the application.")
        except ImportError:
            QMessageBox.critical(self, "Error", "pyscard not installed. Please install required packages.")
            sys.exit(1)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize reader: {str(e)}")
            sys.exit(1)
        
        # Initialize variables
        self.scanning = False
        self.scan_thread = None
        self.tag_queue = queue.Queue()
        self.scan_timeout = 30  # 30 seconds timeout
        
        # Initialize reader, writer, and copier
        self.nfc_reader = NFCReader(self.readers_func, self.toHexString, self.debug_callback)
        self.nfc_writer = NFCWriter(self.toHexString, self.debug_callback)
        self.nfc_copier = NFCCopier(self.nfc_reader, self.nfc_writer, self.debug_callback)
        
        # Setup UI
        self.setup_ui()
        
        # Set up keyboard shortcuts
        self.setup_shortcuts()
        
        # Setup status bar with additional info
        self.setup_status_bar()
        
        self.setMinimumSize(600, 500)  # Set minimum window size
        self.setWindowIcon(QIcon('launcher-icon/acr_1252.ico'))
        self.debug_mode = False  # Debug mode disabled by default
        
        # Connect signals
        self.status_signal.connect(self.update_status_label)
        self.log_signal.connect(self.append_log)
        self.write_status_signal.connect(self.update_write_status)
        self.progress_signal.connect(self.update_progress)
        self.url_signal.connect(self.update_url_label)
        self.progress_value_signal.connect(self.update_progress_bar)
        
        # Start checking for reader
        self.check_reader_timer = QTimer()
        self.check_reader_timer.timeout.connect(self.check_reader)
        self.check_reader_timer.start(2000)
        
        # Setup queue check timer
        self.queue_timer = QTimer()
        self.queue_timer.timeout.connect(self.check_tag_queue)
        self.queue_timer.start(100)
        
        # Apply light theme by default
        self.apply_light_theme()
        
        # Create unified status bar
        self.setup_unified_status_area()
    
    def setup_ui(self):
        """Setup the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget with modern styling
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tab_widget.setTabEnabled(0, True)
        self.tab_widget.setTabEnabled(1, True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background: white;
                margin-top: -1px;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                background: #f5f5f5;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #1976d2;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #eeeeee;
            }
        """)
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.read_tab = ReadTab()
        self.write_tab = WriteTab()
        self.copy_tab = CopyTab()
        self.about_tab = AboutTab()
        
        # Connect tab signals
        self.connect_read_tab_signals()
        self.connect_write_tab_signals()
        self.connect_copy_tab_signals()
        
        # Add tabs to tab widget
        self.tab_widget.addTab(self.read_tab, "Read Tags")
        self.tab_widget.addTab(self.write_tab, "Write Tags")
        self.tab_widget.addTab(self.copy_tab, "Copy Tags")
        self.tab_widget.addTab(self.about_tab, "About")
        
        # Load icon for about tab
        self.load_about_icon()
    
    def connect_read_tab_signals(self):
        """Connect signals from the read tab."""
        self.read_tab.scan_toggled.connect(self.toggle_scanning)
        self.read_tab.copy_log_clicked.connect(self.copy_log)
        self.read_tab.clear_log_clicked.connect(self.clear_log)
        self.read_tab.copy_url_clicked.connect(self.copy_detected_url)
        self.read_tab.debug_toggled.connect(self.toggle_debug_mode)
    
    def connect_write_tab_signals(self):
        """Connect signals from the write tab."""
        self.write_tab.write_clicked.connect(self.write_tag)
        self.write_tab.paste_clicked.connect(self.paste_to_write_entry)
        self.write_tab.clear_clicked.connect(self.clear_write_entry)
        self.write_tab.test_url_clicked.connect(self.test_url)
        self.write_tab.clear_status_clicked.connect(lambda: self.write_tab.update_write_status(""))
        self.write_tab.text_changed.connect(self.validate_write_input)
    
    def connect_copy_tab_signals(self):
        """Connect signals from the copy tab."""
        self.copy_tab.read_source_clicked.connect(self.read_source_tag)
        self.copy_tab.copy_clicked.connect(self.copy_to_new_tag)
        self.copy_tab.reset_clicked.connect(self.reset_copy_operation)
        self.copy_tab.stop_clicked.connect(self.stop_copy_operation)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Paste shortcut
        paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        paste_shortcut.activated.connect(self.paste_to_write_entry)
        
        # Copy shortcut for URL
        copy_url_shortcut = QShortcut(QKeySequence.StandardKey.Copy, self)
        copy_url_shortcut.activated.connect(self.copy_detected_url)
        
        # Clear shortcut (Ctrl+L)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_write_entry)
        
        # Tab shortcuts
        read_tab_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        read_tab_shortcut.activated.connect(lambda: self.tab_widget.setCurrentIndex(0))
        
        write_tab_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        write_tab_shortcut.activated.connect(lambda: self.tab_widget.setCurrentIndex(1))
        
        copy_tab_shortcut = QShortcut(QKeySequence("Ctrl+3"), self)
        copy_tab_shortcut.activated.connect(lambda: self.tab_widget.setCurrentIndex(2))
        
        about_tab_shortcut = QShortcut(QKeySequence("Ctrl+4"), self)
        about_tab_shortcut.activated.connect(lambda: self.tab_widget.setCurrentIndex(3))
        
        # Theme toggle (Ctrl+T) 
        theme_shortcut = QShortcut(QKeySequence("Ctrl+T"), self)
        theme_shortcut.activated.connect(self.toggle_theme)
    
    def setup_status_bar(self):
        """Setup enhanced status bar."""
        # Create permanent widgets for the status bar
        self.tag_status = QLabel("No Tag")
        self.theme_status = QLabel("Light Mode")
        
        # Add permanent widgets to status bar
        self.status_bar.addPermanentWidget(self.tag_status)
        self.status_bar.addPermanentWidget(QLabel("|"))  # Separator
        self.status_bar.addPermanentWidget(self.theme_status)
        
        # Style the status bar
        self.status_bar.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #d0d0d0;
            }
            QLabel {
                padding: 3px 6px;
            }
        """)
    
    def setup_unified_status_area(self):
        """Setup a unified status area that appears in all tabs."""
        # Create a widget to hold the unified status area
        self.unified_status_widget = QWidget()
        self.unified_status_layout = QHBoxLayout(self.unified_status_widget)
        self.unified_status_layout.setContentsMargins(10, 5, 10, 5)
        self.unified_status_layout.setSpacing(10)
        
        # Reader status indicator
        self.reader_indicator = QLabel()
        self.reader_indicator.setFixedSize(15, 15)
        self.reader_indicator.setStyleSheet("background-color: #FFA500; border-radius: 7px;")
        
        # Reader status text
        self.reader_status_text = QLabel("Reader: Not Connected")
        
        # Tag type indicator
        self.tag_type_label = QLabel("Tag Type: Unknown")
        self.tag_type_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        
        # Add to layout
        self.unified_status_layout.addWidget(self.reader_indicator)
        self.unified_status_layout.addWidget(self.reader_status_text)
        self.unified_status_layout.addWidget(self.tag_type_label)
        self.unified_status_layout.addStretch()
        
        # Add to main window at the top
        self.centralWidget().layout().insertWidget(0, self.unified_status_widget)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #d0d0d0;
            }
            QLabel {
                padding: 3px 6px;
            }
        """)
    
    def load_about_icon(self):
        """Load icon for the about tab."""
        try:
            # Try to load from local file first
            pixmap = QPixmap("images/acr_1252.png")
            if not pixmap.isNull():
                self.about_tab.set_icon(pixmap)
                return
            
            # If local file fails, try remote URL
            icon_url = "https://res.cloudinary.com/drrvnflqy/image/upload/v1738978376/acr_1252_jcozss.png"
            response = urllib.request.urlopen(icon_url)
            image_data = response.read()
            
            # Create QPixmap from downloaded data
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(image_data))
            
            if not pixmap.isNull():
                self.about_tab.set_icon(pixmap)
            else:
                raise Exception("Failed to load image")
        except Exception:
            # Create a default icon if image cannot be loaded
            self.about_tab.set_icon(None)
    
    def apply_light_theme(self):
        """Apply light theme to the application."""
        self.setStyleSheet("""
            /* Global styles */
            QMainWindow, QWidget {
                background-color: #ffffff;
                color: #000000;
                font-family: 'Ubuntu', 'Segoe UI', sans-serif;
            }
            
            /* Main window style */
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #e8e8e8);
            }
            
            /* Add spacing between sections */
            QGroupBox {
                margin-top: 15px;
                margin-bottom: 5px;
            }
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background-color: #ffffff;
                border-radius: 4px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #000000;
                padding: 14px 32px;
                border: 1px solid #d0d0d0;
                border-bottom: none;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 2px solid #1976d2;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e8e8e8;
            }
            QLabel {
                color: #000000;
            }
            QLabel#status_label {
                color: #1976d2;
                font-weight: 600;
                padding: 8px;
                background-color: #e3f2fd;
                border-radius: 4px;
                margin: 5px 0;
                font-size: 13px;
                border: 1px solid #bbdefb;
                min-height: 18px;
            }
            
            QPushButton {
                background-color: #1976d2;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                min-width: 120px;
                font-size: 13px;
                border: 1px solid rgba(0,0,0,0.2);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e88e5, stop:1 #1976d2);
            }
            
            QPushButton:disabled {
                background-color: #bdbdbd;
                color: #757575;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
            QPushButton:pressed {
                background-color: #1565c0;
            }
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #bbdefb;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #bbdefb;
                font-family: 'Segoe UI';
                font-size: 14px;
                min-width: 200px;
                min-height: 24px;
                margin-right: 5px;
            }
            
            QLineEdit:focus {
                border: 2px solid #1976d2;
            }
            QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                min-width: 80px;
                min-height: 24px;
                padding: 6px;
            }
            QGroupBox {
                border: 1px solid #d0d0d0;
                border-radius: 12px;
                margin-top: 1.5em;
                padding-top: 1.5em;
                padding: 15px;
                color: #000000;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f8f8);
                border: 1px solid rgba(0,0,0,0.15);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QCheckBox {
                color: #000000;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #d0d0d0;
                background-color: #ffffff;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #1976d2;
                background-color: #1976d2;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgdmlld0JveD0iMCAwIDE2IDE2Ij48cGF0aCBmaWxsPSIjZmZmIiBkPSJNNi4yIDEwLjhsLTMtMy0xLjQgMS40IDQuNCA0LjQgOC44LTguOC0xLjQtMS40eiIvPjwvc3ZnPg==);
            }
        """)
        self.theme_status.setText("Light Mode")
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #3d3d3d;
                    background-color: #2b2b2b;
                }
                QTabBar::tab {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                }
                QTabBar::tab:selected {
                    background-color: #2b2b2b;
                    border-bottom: 2px solid #1976d2;
                }
                QLineEdit, QTextEdit, QComboBox {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #4d4d4d;
                }
                QPushButton {
                    background-color: #1976d2;
                    color: white;
                    border: none;
                }
                QGroupBox {
                    border: 1px solid #4d4d4d;
                    color: #ffffff;
                }
            """)
            self.theme_status.setText("Dark Mode")
        else:
            self.apply_light_theme()
    
    def check_reader(self):
        """Check for ACR1252U reader and update status."""
        result, message = self.nfc_reader.find_reader()
        if result:
            self.read_tab.update_status(f"Status: {message}")
            self.status_bar.showMessage(f"{message} and ready")
            self.reader_status_text.setText(f"Reader: {message}")
            self.reader_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 7px;")  # Green
            
            # Animate the reader indicator
            self.animate_indicator(self.reader_indicator)
        else:
            self.reader_status_text.setText("Reader: Not Connected")
            self.reader_indicator.setStyleSheet("background-color: #FFA500; border-radius: 7px;")  # Orange
            self.tag_type_label.setText("Tag Type: Unknown")
            
            # Update status messages
            self.read_tab.update_status(f"Status: {message}")
            self.status_bar.showMessage("Reader not found - Please connect an NFC reader")
    
    def on_tab_changed(self, index):
        """Handle tab change events."""
        if (index == 1 or index == 2) and self.scanning:  # Index 1 is Write Tags tab, Index 2 is Copy Tags tab
            self.toggle_scanning(False)  # Stop scanning when switching to write tab
        if index == 2 and self.nfc_copier.copying:  # Index 2 is Copy Tags tab
            self.stop_copy_operation()  # Stop copying when switching away from copy tab
    
    def animate_indicator(self, indicator):
        """Create a pulsing animation for an indicator."""
        # Create animation for size
        self.pulse_animation = QPropertyAnimation(indicator, b"size")
        self.pulse_animation.setDuration(300)
        self.pulse_animation.setStartValue(QSize(15, 15))
        self.pulse_animation.setEndValue(QSize(18, 18))
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        # Make it pulse by going back and forth
        self.pulse_animation.finished.connect(lambda: self.pulse_animation.setDirection(
            QPropertyAnimation.Direction.Backward if self.pulse_animation.direction() == QPropertyAnimation.Direction.Forward else QPropertyAnimation.Direction.Forward))
        self.pulse_animation.start()
    
    def toggle_scanning(self, start_scanning=None):
        """Toggle the scanning process."""
        if start_scanning is None:
            start_scanning = not self.scanning
        
        if start_scanning and not self.scanning:
            self.scanning = True
            self.read_tab.scan_button.setText("Stop Scanning")
            self.read_tab.scan_button.setStyleSheet("background-color: #c62828;")  # Red for stop
            self.append_log("System", f"Started scanning for tags (will timeout after {self.scan_timeout} seconds of inactivity)")
            self.scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
            self.scan_thread.start()
        elif not start_scanning and self.scanning:
            self.scanning = False
            self.read_tab.scan_button.setText("Start Scanning")
            self.read_tab.scan_button.setStyleSheet("")  # Reset to default style
            self.append_log("System", "Stopped scanning")
    
    def scan_loop(self):
        """Continuous scanning loop."""
        last_uid = None
        last_activity_time = time.time()
        
        while self.scanning:
            # Check for timeout
            if time.time() - last_activity_time > self.scan_timeout:
                self.append_log("System", f"Scanning stopped after {self.scan_timeout} seconds of inactivity")
                self.scanning = False
                # Update UI from main thread
                self.status_signal.emit("Status: Scanning timed out - No recent activity")
                break
            
            try:
                if self.nfc_reader.reader:
                    connection, connected = self.nfc_reader.connect_with_retry()
                    if not connected:
                        time.sleep(0.2)
                        continue
                    
                    # Get UID
                    uid = self.nfc_reader.get_tag_uid(connection)
                    if uid:
                        # Update UI via signals
                        self.status_signal.emit("Tag Ready")                        
                        self.write_status_signal.emit("Tag Ready - Click Write to proceed")
                        self.write_tab.update_tag_status(True)
                        self.tag_status.setText("Tag Present")  # Update status bar
                        
                        # Detect tag type
                        try:
                            tag_type = self.nfc_reader.detect_tag_type(connection)
                            self.tag_type_label.setText(f"Tag Type: {tag_type}")
                        except Exception as e:
                            # Handle exception during tag type detection
                            if self.debug_mode:
                                self.append_log("Error", f"Tag type detection failed: {str(e)}")
                            self.tag_type_label.setText("Tag Type: Unknown")
                        
                        # Animate tag indicator in write tab
                        if hasattr(self.write_tab, 'tag_indicator'):
                            self.animate_indicator(self.write_tab.tag_indicator)
                            
                        last_activity_time = time.time()
                        
                        # Only process if it's a new tag
                        if uid != last_uid:
                            last_uid = uid
                            self.append_log("New tag detected", f"UID: {uid}")
                            
                            # Read tag memory
                            try:
                                memory_data = self.nfc_reader.read_tag_memory(connection)
                                if memory_data:
                                    self.process_ndef_content(memory_data)
                            except Exception as e:
                                # Handle exception during tag memory reading
                                if self.debug_mode:
                                    self.append_log("Error", f"Failed to read tag memory: {str(e)}")
                    
                    connection.disconnect()
            except Exception as e:
                error_msg = str(e)
                # Only log errors that aren't common disconnection messages
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]):
                    self.append_log("Error", f"Scan error: {error_msg}")
                
                last_uid = None  # Reset UID on error
                self.write_tab.update_tag_status(False)  # Update status when tag is removed/error
            
            time.sleep(0.2)  # Delay between scans
    
    def process_ndef_content(self, data: List[int]):
        """Process NDEF content and open URLs if found."""
        try:
            url = extract_url_from_data(data, self.toHexString)
            if url:
                self.append_log("URL Detected", f"Found URL: {url}")
                self.url_signal.emit(url)
                
                # Open URL in browser in a separate thread to prevent blocking UI
                def open_url_thread():
                    try:
                        if open_url_in_browser(url):
                            self.log_signal.emit("System", "Opening URL in browser")
                        else:
                            self.log_signal.emit("Error", f"Failed to open URL in browser: {url}")
                    except Exception as e:
                        self.log_signal.emit("Error", f"Error opening URL: {str(e)}")
                
                # Start the thread
                threading.Thread(target=open_url_thread, daemon=True).start()
                
        except Exception as e:
            self.append_log("Error", f"Error parsing NDEF: {str(e)}")
    
    @pyqtSlot()
    def check_tag_queue(self):
        """Check for new tag data and update the GUI."""
        try:
            while True:
                title, message = self.tag_queue.get_nowait()
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                self.read_tab.append_log(title, message, timestamp, self._get_title_color(title))
        except queue.Empty:
            pass
    
    def copy_detected_url(self):
        """Copy detected URL to clipboard."""
        url = self.read_tab.url_label.text()
        if url:
            QApplication.clipboard().setText(url)
            self.append_log("System", "URL copied to clipboard")
    
    def copy_log(self):
        """Copy log content to clipboard."""
        content = self.read_tab.get_log_text()
        QApplication.clipboard().setText(content)
        self.append_log("System", "Log content copied to clipboard")
    
    def clear_log(self):
        """Clear the log text."""
        self.read_tab.clear_log()
        self.append_log("System", "Log cleared")
    
    def _get_title_color(self, title):
        """Get color for log message title."""
        colors = {
            "Error": "#D32F2F",
            "Debug": "#1976D2",
            "System": "#388E3C",
            "URL Detected": "#7B1FA2",
            "Browser": "#F57C00",
            "Text Record": "#00796B"
        }
        return colors.get(title, "#000000")
    
    def toggle_debug_mode(self, state):
        """Toggle debug mode on/off."""
        self.debug_mode = bool(state)
        if not self.debug_mode:
            self.read_tab.clear_log()
            self.append_log("System", "Debug mode disabled")
        else:
            self.append_log("System", "Debug mode enabled")
    
    def debug_callback(self, title, message):
        """Callback for debug messages."""
        self.log_signal.emit(title, message)
    
    def append_log(self, title, message):
        """Append formatted message to log."""
        # Only show debug messages if debug mode is enabled
        if title == "Debug" and not self.debug_mode:
            return
        
        # Only show important messages by default
        if not self.debug_mode and title not in ["Error", "URL Detected", "System", "Text Record"]:
            return
        
        try:
            # Check if the read tab still exists
            if hasattr(self, 'read_tab') and self.read_tab is not None:
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                self.read_tab.append_log(title, message, timestamp, self._get_title_color(title))
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    @pyqtSlot(str)
    def update_status_label(self, text):
        """Update the status label."""
        try:
            # Check if the read tab still exists
            if hasattr(self, 'read_tab') and self.read_tab is not None:
                self.read_tab.update_status(text)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    @pyqtSlot(str)
    def update_write_status(self, text):
        """Update the write status label."""
        try:
            # Check if the write tab still exists
            if hasattr(self, 'write_tab') and self.write_tab is not None:
                self.write_tab.update_write_status(text)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    @pyqtSlot(str)
    def update_progress(self, text):
        """Update the progress label."""
        try:
            # Check if the write tab still exists
            if hasattr(self, 'write_tab') and self.write_tab is not None:
                self.write_tab.update_progress(text)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    @pyqtSlot(int, int)
    def update_progress_bar(self, current, total):
        """Update the progress bar."""
        try:
            # Check if the write tab still exists
            if hasattr(self, 'write_tab') and self.write_tab is not None:
                self.write_tab.update_progress_bar(current, total)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    @pyqtSlot(str)
    def update_url_label(self, text):
        """Update the URL label."""
        try:
            # Check if the read tab still exists
            if hasattr(self, 'read_tab') and self.read_tab is not None:
                self.read_tab.update_url(text)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def write_tag(self):
        """Write data to multiple tags."""
        # Get URL from text field
        text = self.write_tab.get_url()
        if not text:
            QMessageBox.critical(self, "Error", "Please enter a URL to write")
            return
        
        # Check if URL starts with http://, https://, or www.
        if not (text.startswith('http://') or text.startswith('https://') or text.startswith('www.')):
            result = QMessageBox.warning(
                self, 
                "URL Format Warning",
                "The URL should start with http://, https://, or www.\n\n"
                "Would you like to automatically add 'https://' to the URL?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if result == QMessageBox.StandardButton.Yes:
                text = 'https://' + text
                self.write_tab.set_url(text)
                self.validate_write_input(text)
            else:
                return
        
        # Validate URL format
        is_valid, normalized_url = validate_url(text)
        if not is_valid:
            QMessageBox.warning(self, "Warning", "The URL format appears to be invalid. Please check and try again.")
            return
        
        # Update with normalized URL
        if normalized_url != text:
            self.write_tab.set_url(normalized_url)
            text = normalized_url
        
        quantity = self.write_tab.get_quantity()
        if quantity < 1:
            QMessageBox.critical(self, "Error", "Quantity must be at least 1")
            return
        
        lock = self.write_tab.get_lock_state()
        
        # Use signals to update UI elements instead of direct calls
        self.write_status_signal.emit("Ready - Please present first tag...")
        self.progress_signal.emit(f"Starting batch operation: 0/{quantity} tags written")
        
        # Add to recent URLs
        self.write_tab.add_recent_url(text)
        
        # Start batch write in a separate thread
        threading.Thread(
            target=self.nfc_writer.batch_write_tags,
            args=(self.nfc_reader, text, quantity, lock),
            kwargs={
                'progress_callback': self.on_write_progress,
                'status_callback': self.on_write_status
            },
            daemon=True
        ).start()
    
    def on_write_progress(self, tags_written, total):
        """Callback for write progress updates."""
        self.progress_signal.emit(f"{tags_written}/{total} tags written")
        self.progress_value_signal.emit(tags_written, total)
    
    def on_write_status(self, text):
        """Callback for write status updates."""
        self.write_status_signal.emit(text)
    
    def validate_write_input(self, text):
        """Validate URL input and provide feedback."""
        text = text.strip()
        
        # Update character count
        remaining = 137 - len(text)  # NTAG213 URL capacity
        self.write_tab.update_char_count(remaining)
        
        # Validate URL format
        is_valid = False
        if text:
            is_valid, _ = validate_url(text)
        
        # Update validation label
        if is_valid:
            self.write_tab.update_validation(True, "Valid URL format")
        elif text:
            self.write_tab.update_validation(False, "Invalid URL format - Must start with http://, https://, or www.")
        else:
            self.write_tab.update_validation(False, "")
        
        # Enable/disable write button
        self.write_tab.update_write_button(is_valid and remaining >= 0)
    
    def paste_to_write_entry(self):
        """Paste clipboard content into write entry."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        
        if text:
            self.write_tab.set_url(text)
            self.validate_write_input(text)
            self.append_log("System", f"URL updated to: {text}")
    
    def clear_write_entry(self):
        """Clear the write entry field."""
        self.write_tab.set_url("")
        self.validate_write_input("")
    
    def test_url(self):
        """Test the URL by opening it in the default browser."""
        url = self.write_tab.get_url()
        if url:
            if open_url_in_browser(url):
                self.append_log("System", "Testing URL in browser")
            else:
                self.append_log("Error", "Failed to open URL in browser")
    
    def read_source_tag(self):
        """Read a source tag for copying."""
        if not self.nfc_reader.reader:
            QMessageBox.critical(self, "Error", "Reader not connected")
            return
        
        # Update UI
        self.copy_tab.update_status("Status: Please present source tag to read...")
        self.copy_tab.update_source_info("Waiting for source tag...")
        self.copy_tab.enable_copy_button(False)
        
        # Start a thread to read the source tag
        threading.Thread(
            target=self.nfc_copier.read_source_tag,
            kwargs={
                'status_callback': self.on_copy_status,
                'tag_info_callback': self.on_tag_info
            },
            daemon=True
        ).start()
    
    def copy_to_new_tag(self):
        """Copy source tag data to new tags."""
        if not self.nfc_copier.source_tag_data:
            QMessageBox.critical(self, "Error", "No source tag data available")
            return
            
        if not self.nfc_reader.reader:
            QMessageBox.critical(self, "Error", "Reader not connected")
            return
        
        # Get copy settings
        quantity = self.copy_tab.get_copies_count()
        lock = self.copy_tab.get_lock_state()
        
        # Update UI
        self.copy_tab.enable_copy_button(False)
        self.copy_tab.enable_stop_button(True)
        self.copy_tab.enable_read_button(False)
        
        # Start copy operation in a separate thread
        threading.Thread(
            target=self.nfc_copier.copy_to_new_tags,
            args=(quantity, lock),
            kwargs={
                'status_callback': self.on_copy_status,
                'progress_callback': self.on_copy_progress
            },
            daemon=True
        ).start()
    
    def on_copy_status(self, text):
        """Callback for copy status updates."""
        self.copy_tab.update_status(text)
    
    def on_tag_info(self, text):
        """Callback for tag info updates."""
        self.copy_tab.update_source_info(text)
        self.copy_tab.enable_copy_button(True)
    
    def on_copy_progress(self, current, total):
        """Callback for copy progress updates."""
        self.copy_tab.update_progress(f"{current}/{total} tags written")
        self.copy_tab.update_progress_bar(current, total)
        
        # If all copies are done, update UI
        if current == total:
            self.copy_tab.enable_stop_button(False)
            self.copy_tab.enable_read_button(True)
    
    def reset_copy_operation(self):
        """Reset the copy operation."""
        self.nfc_copier.reset()
        self.copy_tab.update_source_info("No source tag scanned yet")
        self.copy_tab.update_progress("")
        self.copy_tab.update_status("Status: Operation reset")
        self.copy_tab.enable_copy_button(False)
        self.copy_tab.enable_read_button(True)
        self.copy_tab.enable_stop_button(False)
        self.copy_tab.update_tag_status(False)
    
    def stop_copy_operation(self):
        """Stop the ongoing copy operation."""
        self.nfc_copier.stop_copy_operation()
        self.copy_tab.update_status("Status: Copy operation stopped")
        self.copy_tab.enable_stop_button(False)
        self.copy_tab.enable_copy_button(True)
        self.copy_tab.enable_read_button(True)
