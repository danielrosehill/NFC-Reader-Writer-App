#!/usr/bin/env python3

import sys
import threading
import time
import queue
import subprocess
import re
import ssl
import urllib.request
import urllib.error
from typing import Optional, List, Tuple
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                            QTextEdit, QLineEdit, QSpinBox, QCheckBox, 
                            QGroupBox, QFrame, QMessageBox, QSizePolicy,
                            QComboBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon, QPixmap
from PyQt6.QtCore import QSize

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
        self.setMinimumSize(1000, 800)
        self.setWindowIcon(QIcon('launcher-icon/acr_1252.ico'))
        self.debug_mode = False  # Debug mode disabled by default
        
        # Initialize reader
        try:
            from smartcard.System import readers
            from smartcard.util import toHexString
            from smartcard.Exceptions import NoReadersException
            self.readers = readers
            self.toHexString = toHexString
            
            # Verify reader availability immediately
            self.available_readers = self.readers()
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
        self.last_connection_time = 0
        self.last_activity_time = 0
        self.scan_timeout = 30  # 30 seconds timeout
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

        # Apply light theme by default
        # Create status bar
        self.statusBar = self.statusBar()
        self.statusBar.showMessage("Ready")
        
        self.apply_light_theme()

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
                color: #1565c0;
                font-weight: bold;
                padding: 16px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e3f2fd, stop:1 #bbdefb);
                border-radius: 8px;
                margin: 8px 0;
                font-size: 14px;
                border: 1px solid rgba(25, 118, 210, 0.2);
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
                min-height: 24px;
            }
            
            QLineEdit:focus {
                border: 2px solid #1976d2;
            }
            QSpinBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
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
                padding: 16px 40px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                background: #f5f5f5;
                font-size: 14px;
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
        self.read_tab = QWidget()
        self.write_tab = QWidget()
        self.about_tab = QWidget()
        self.tab_widget.addTab(self.read_tab, "Read Tags")
        self.tab_widget.addTab(self.write_tab, "Write Tags")
        self.tab_widget.addTab(self.about_tab, "About")
        
        # Setup read interface
        self.setup_read_interface()
        
        # Setup write interface
        self.setup_write_interface()
        
        # Setup about interface
        self.setup_about_interface()

    def setup_read_interface(self):
        """Setup the read tab interface."""
        layout = QVBoxLayout(self.read_tab)
        
        # Status section with modern card-like design
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 8px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(16, 16, 16, 16)
        
        self.status_label = QLabel("Status: Waiting for reader...")
        self.status_label.setObjectName("status_label")
        self.status_label.setMinimumHeight(40)  # Increase height for better visibility
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
        self.url_label.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 12px;
                color: #1976D2;
                padding: 8px;
                background-color: #E3F2FD;
                border-radius: 4px;
            }
        """)
        self.copy_url_button = QPushButton("📋")
        self.copy_url_button.setToolTip("Copy URL to clipboard")
        self.copy_url_button.clicked.connect(self.copy_detected_url)
        self.copy_url_button.setFixedSize(40, 40)
        self.copy_url_button.setStyleSheet("""
            QPushButton { 
                color: #1976d2;
                background-color: white;
                border: 1px solid #1976d2;
                border-radius: 20px;
                font-size: 20px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
            }
        """)
        url_layout.addWidget(self.url_label)
        url_layout.addWidget(self.copy_url_button)
        layout.addWidget(url_group)
        
        # Log group with debug toggle
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        # Add debug mode toggle
        debug_container = QWidget()
        debug_layout = QHBoxLayout(debug_container)
        debug_layout.setContentsMargins(0, 0, 0, 10)
        
        self.debug_checkbox = QCheckBox("Debug Mode")
        self.debug_checkbox.setChecked(False)
        self.debug_checkbox.stateChanged.connect(self.toggle_debug_mode)
        debug_layout.addWidget(self.debug_checkbox)
        debug_layout.addStretch()
        
        log_layout.addWidget(debug_container)
        
        # Log text area with enhanced styling
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Segoe UI", 10))
        self.log_text.setStyleSheet("""
            QTextEdit, QTextEdit * {
                font-family: 'Segoe UI' !important;
                line-height: 1.6;
                padding: 10px;
                background-color: #FFFFFF;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Button container with improved styling
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 8, 0, 0)
        button_layout.setSpacing(12)
        
        # Copy and Clear buttons with icons and tooltips
        self.copy_button = QPushButton("📋 Copy Log")
        self.copy_button.clicked.connect(self.copy_log)
        self.copy_button.setToolTip("Copy log contents to clipboard")
        self.copy_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        self.clear_button = QPushButton("🗑️ Clear Log")
        self.clear_button.clicked.connect(self.clear_log)
        self.clear_button.setToolTip("Clear all log entries")
        self.clear_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()
        
        log_layout.addWidget(button_container)
        layout.addWidget(log_group)

    def setup_about_interface(self):
        """Setup the about tab interface."""
        layout = QVBoxLayout(self.about_tab)
        
        # Header section with app info
        header_group = QGroupBox("About NFC Reader/Writer")
        header_layout = QVBoxLayout(header_group)
        
        # App icon
        icon_label = QLabel()
        # Load icon from remote URL
        icon_url = "https://res.cloudinary.com/drrvnflqy/image/upload/v1738978376/acr_1252_jcozss.png"
        try:
            import urllib.request
            from PyQt6.QtCore import QByteArray
            
            # Download image data
            response = urllib.request.urlopen(icon_url)
            image_data = response.read()
            
            # Create QPixmap from downloaded data
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(image_data))
            
            # Scale to desired size
            icon_pixmap = pixmap.scaled(QSize(64, 64), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            if icon_pixmap.isNull():
                raise Exception("Failed to load image")
        except Exception as e:
            # Create a default icon if image cannot be loaded
            pixmap = QPixmap(64, 64)
            pixmap.fill(QColor("#1976d2"))  # Use theme color
            icon_pixmap = pixmap
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)
        
        # Version info
        version_label = QLabel("Version 3.2")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("font-weight: bold; color: #1976d2; margin: 10px 0;")
        header_layout.addWidget(version_label)
        
        # Description
        desc_label = QLabel(
            "A user-friendly application for reading and writing NFC tags using the ACR1252U reader. "
            "Perfect for managing URL tags, text records, and batch operations."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("margin: 10px 0;")
        header_layout.addWidget(desc_label)
        
        layout.addWidget(header_group)
        
        # Attribution section
        attribution_group = QGroupBox("Attribution")
        attribution_layout = QVBoxLayout(attribution_group)
        
        # Developer info with link
        dev_label = QLabel(
            "Developed by <a style='color: #1976d2;' href='https://danielrosehill.com'>Daniel Rosehill</a> "
            "and Claude 3.5 Sonnet"
        )
        dev_label.setOpenExternalLinks(True)
        dev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        attribution_layout.addWidget(dev_label)
        
        # GitHub repo link
        repo_label = QLabel(
            "Source code: <a style='color: #1976d2;' href='https://github.com/danielrosehill/NFC-Reader-Writer-App/'>"
            "GitHub Repository</a>"
        )
        repo_label.setOpenExternalLinks(True)
        repo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        attribution_layout.addWidget(repo_label)
        
        layout.addWidget(attribution_group)
        
        # User Manual section
        manual_group = QGroupBox("User Manual")
        manual_layout = QVBoxLayout(manual_group)
        
        manual_text = QTextEdit()
        manual_text.setReadOnly(True)
        manual_text.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: none;
                padding: 15px;
            }
        """)
        manual_text.setHtml("""
            <style>
                h3 { color: #1976d2; margin-bottom: 15px; }
                h4 { color: #2196f3; margin-top: 20px; margin-bottom: 10px; }
                p { line-height: 1.6; margin-bottom: 15px; }
                ol, ul { margin-left: 20px; line-height: 1.6; }
                li { margin-bottom: 8px; }
                .tip { 
                    background-color: #e3f2fd; 
                    padding: 10px 15px; 
                    border-radius: 4px;
                    margin: 10px 0;
                }
                .feature {
                    color: #1976d2;
                    font-weight: bold;
                }
            </style>
            
            <h3>Quick Start Guide</h3>
            <p>Welcome to the NFC Reader/Writer application! This tool helps you interact with NFC tags using the ACR1252U reader.</p>
            
            <h4>Reading Tags</h4>
            <ol>
                <li><span class='feature'>Connect</span> your ACR1252U reader to your computer</li>
                <li>Navigate to the <span class='feature'>"Read Tags"</span> tab</li>
                <li>Click the <span class='feature'>"Start Scanning"</span> button</li>
                <li>Present an NFC tag to the reader</li>
                <li>The detected URL or text will be displayed automatically</li>
            </ol>
            
            <h4>Writing Tags</h4>
            <ol>
                <li>Go to the <span class='feature'>"Write Tags"</span> tab</li>
                <li>Enter the URL or text you want to write</li>
                <li>Set the number of tags for batch writing (optional)</li>
                <li>Choose whether to lock tags after writing</li>
                <li>Click <span class='feature'>"Write to Tag"</span> and follow the prompts</li>
            </ol>
            
            <h4>Copying Tags</h4>
            <ol>
                <li>Navigate to the <span class='feature'>"Copy Tags"</span> tab</li>
                <li>Click <span class='feature'>"Read & Store Tag"</span> with your source tag</li>
                <li>Present a new tag and click <span class='feature'>"Copy to New Tag"</span></li>
                <li>Repeat for additional copies (up to 10 copies allowed)</li>
            </ol>
            
            <h4>Status Indicators</h4>
            <div class='tip'>
                <p>The colored indicator shows the current tag status:</p>
                <ul>
                    <li>🟧 <span class='feature'>Orange</span> = No tag present</li>
                    <li>🟩 <span class='feature'>Green</span> = Tag detected</li>
                    <li>✅ <span class='feature'>Green with checkmark</span> = Tag locked</li>
                </ul>
            </div>
        """)
        manual_layout.addWidget(manual_text)
        
        layout.addWidget(manual_group)

    def setup_write_interface(self):
        """Setup the write tab interface."""
        layout = QVBoxLayout(self.write_tab)
        
        # Quick Write section for single tags
        quick_write_group = QGroupBox("Quick Write")
        quick_write_layout = QHBoxLayout(quick_write_group)
        
        self.quick_write_button = QPushButton("Quick Write Single Tag")
        self.quick_write_button.setToolTip("Quickly write the current URL to a single tag")
        self.quick_write_button.clicked.connect(lambda: self.batch_write_tags(self.write_entry.text().strip(), 1))
        self.quick_write_button.setEnabled(False)
        self.quick_write_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                padding: 12px 24px;
            }
        """)
        
        quick_write_layout.addWidget(self.quick_write_button)
        layout.addWidget(quick_write_group)
        
        # Input section
        input_group = QGroupBox("Tag Content")
        input_layout = QVBoxLayout(input_group)
        
        # URL input with tooltip
        input_label = QLabel("Enter URL to write to tag:")
        input_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        input_label.setStyleSheet("color: #1976d2; margin-bottom: 8px;")
        input_label.setToolTip("Enter a complete URL starting with http://, https://, or www.")
        
        # Add validation label
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("margin-top: 5px;")
        
        # Add character counter
        self.char_count_label = QLabel("Characters remaining: 137")
        self.char_count_label.setStyleSheet("color: #666666; margin-top: 5px;")
        
        # Input container with buttons
        input_container = QWidget()
        input_container_layout = QHBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Recent URLs dropdown
        self.recent_urls = []
        self.url_combo = QComboBox()
        self.url_combo.setMinimumWidth(500)
        self.url_combo.setMinimumHeight(40)
        self.url_combo.setEditable(True)
        self.url_combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.url_combo.currentTextChanged.connect(self.validate_write_input)
        self.write_entry = self.url_combo.lineEdit()
        self.write_entry.setStyleSheet("""
            QLineEdit {
                font-family: 'Segoe UI';
                font-size: 16px;
                padding: 8px 12px;    /* Vertical and horizontal padding */
                border: none;
                margin-bottom: 25px;  /* Keep the spacing below */
                margin-top: 10px;     /* Keep the spacing above */
            }
        """)
        
        # Paste button with circular icon style
        paste_button = QPushButton("📋")
        paste_button.setToolTip("Paste from clipboard")
        paste_button.clicked.connect(self.paste_to_write_entry)
        paste_button.setFixedSize(40, 40)
        paste_button.setStyleSheet("""
            QPushButton { 
                color: #1976d2;
                background-color: white;
                border: 1px solid #1976d2;
                border-radius: 20px;
                font-size: 20px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
            }
        """)
        
        # Clear button with circular icon style
        clear_button = QPushButton("🗑️")
        clear_button.setToolTip("Clear input")
        clear_button.clicked.connect(self.clear_write_entry)
        clear_button.setFixedSize(40, 40)
        clear_button.setStyleSheet("""
            QPushButton { 
                color: #f44336;
                background-color: white;
                border: 1px solid #f44336;
                border-radius: 20px;
                font-size: 20px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #ffebee;
            }
        """)
        
        input_container_layout.addWidget(self.write_entry)
        input_container_layout.addWidget(paste_button)
        input_container_layout.addWidget(clear_button)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(input_container)
        input_layout.addWidget(self.validation_label)
        input_layout.addWidget(self.char_count_label)
        
        # Add test URL button next to input
        test_url_button = QPushButton("🔗 Test URL")
        test_url_button.setToolTip("Open URL in browser to test")
        test_url_button.clicked.connect(self.test_url)
        test_url_button.setFixedWidth(120)
        input_container_layout.addWidget(test_url_button)
        
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
        options_group = QGroupBox("Writing Options")
        options_layout = QHBoxLayout(options_group)
        
        self.lock_checkbox = QCheckBox("Lock tag after writing")
        self.lock_checkbox.setChecked(True)
        options_layout.addWidget(self.lock_checkbox)
        
        self.write_button = QPushButton("Write Tag")
        self.write_button.clicked.connect(self.write_tag)
        self.write_button.setFixedWidth(200)
        self.write_button.setEnabled(False)  # Disabled by default
        
        # Connect text changed signal to enable/disable button
        self.write_entry.textChanged.connect(self.validate_write_input)
        options_layout.addWidget(self.write_button)
        options_layout.addStretch()
        
        layout.addWidget(options_group)
        
        # Combined Progress & Status section with enhanced visibility
        status_group = QGroupBox("Status & Progress")
        status_group.setStyleSheet("""
            QGroupBox {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 2em;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #1976d2;
            }
        """)
        status_layout = QHBoxLayout(status_group)
        status_layout.setContentsMargins(16, 24, 16, 16)
        status_layout.setSpacing(16)
        
        # Progress label
        self.progress_label = QLabel("")
        status_layout.addWidget(self.progress_label)
        
        # Add spacer
        status_layout.addSpacing(20)
        
        # Tag detection status
        tag_status_widget = QWidget()
        tag_status_layout = QHBoxLayout(tag_status_widget)
        tag_status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tag_indicator = QLabel()
        self.tag_indicator.setFixedSize(15, 15)
        self.tag_indicator.setStyleSheet("background-color: #FFA500; border-radius: 7px;")  # Orange by default
        
        self.tag_status_label = QLabel("No Tag Present")
        tag_status_layout.addWidget(self.tag_indicator)
        tag_status_layout.addWidget(self.tag_status_label)
        tag_status_layout.addStretch()
        
        # Write status
        write_status_widget = QWidget()
        write_status_layout = QHBoxLayout(write_status_widget)
        write_status_layout.setContentsMargins(0, 0, 0, 0)
        
        self.write_status = QLabel("")
        write_status_layout.addWidget(self.write_status)
        
        self.clear_status_button = QPushButton("Clear Status")
        self.clear_status_button.clicked.connect(lambda: self.write_status.setText(""))
        write_status_layout.addWidget(self.clear_status_button)
        
        status_layout.addWidget(tag_status_widget)
        status_layout.addWidget(write_status_widget)
        layout.addWidget(status_group)
        layout.addStretch()

    def check_reader(self):
        """Check for ACR1252U reader and update status."""
        try:
            available_readers = self.readers()
            self.reader = None
            
            for r in available_readers:
                # Get reader details
                reader_str = str(r)
                reader_id = reader_str.split(" ")[0]
                
                # Known NFC reader models and their capabilities
                reader_models = {
                    "ACR1252": "ACR1252U",
                    "ACR122": "ACR122U",
                    "ACS ACR": "ACS Reader",  # More specific ACS match
                    "SCM Microsystems": "SCM Reader",
                    "OMNIKEY": "HID Omnikey",
                    "Sony": "Sony RC-S380",
                    "PN53": "PN532"
                }
                
                # List of known non-NFC readers to ignore
                ignored_readers = [
                    "Yubico",
                    "YubiKey",
                    "Smart Card Reader",  # Generic smart card readers
                    "USB Smart Card Reader",
                    "Common Access Card",
                    "CAC Reader",
                    "PIV Reader",
                    "EMV Reader"
                ]
                
                # Check if this is a reader we should ignore
                if any(ignored in reader_str for ignored in ignored_readers):
                    continue
                
                # Find matching reader model
                reader_model = None
                for model_id, model_name in reader_models.items():
                    if model_id in reader_str:
                        reader_model = model_name
                        break
                
                # Only proceed if we found a known NFC reader model
                if reader_model is None:
                    continue
                
                self.reader = r
                self.status_signal.emit(f"Status: {reader_model} connected ({reader_id})")
                self.statusBar.showMessage(f"{reader_model} {reader_id} connected and ready")
                return

            self.status_signal.emit("Status: No NFC reader found")
            self.statusBar.showMessage("Reader not found - Please connect an NFC reader")
        except Exception as e:
            error_msg = f"Status: Error - {str(e)}"
            self.status_signal.emit(error_msg)
            self.statusBar.showMessage("Reader error - Check connection")

    def connect_with_retry(self) -> Tuple[any, bool]:
        """Try to connect to the card with retries."""
        current_time = time.time()
        if current_time - self.last_connection_time < 0.1:  # Reduced debounce time
            return None, False
            
        self.last_connection_time = current_time
        
        try:
            connection = self.reader.createConnection()
        except Exception as e:
            self.log_signal.emit("Error", f"Failed to create connection: {str(e)}")
            return None, False
        
        # Try different protocols with retries
        for attempt in range(5):  # Increased retry attempts
            for protocol in ['T1', 'T0', 'T=1', 'T=0', None]:
                try:
                    if protocol:
                        if protocol.startswith('T='):
                            connection.connect(protocol=protocol)
                        else:
                            connection.connect(cardProtocol=protocol)
                    else:
                        connection.connect()
                        
                    # Verify connection with GET_UID command
                    try:
                        response, sw1, sw2 = connection.transmit(self.GET_UID)
                        if sw1 == 0x90:
                            self.log_signal.emit("Debug", f"Connected with protocol: {protocol}")
                            return connection, True
                    except:
                        # If UID check fails, connection might not be stable
                        continue
                        
                except Exception as e:
                    if attempt == 4:  # Only log on last attempt
                        self.log_signal.emit("Debug", f"Connection attempt failed with {protocol}: {str(e)}")
                    time.sleep(0.1 * (attempt + 1))
                    
                try:
                    connection.disconnect()
                except:
                    pass
                    
        self.log_signal.emit("Debug", "All connection attempts failed")
        return None, False

    def read_tag_memory(self, connection) -> List[int]:
        """Read NTAG213 memory pages."""
        all_data = []
        
        # First verify tag presence with UID check
        try:
            response, sw1, sw2 = connection.transmit(self.GET_UID)
            if sw1 != 0x90:
                self.log_signal.emit("Error", f"Tag presence check failed: SW1={sw1:02X} SW2={sw2:02X}")
                return []
        except Exception as e:
            self.log_signal.emit("Error", f"UID check failed: {str(e)}")
            return []
            
        # Read capability container (CC) first
        try:
            cc_cmd = self.READ_PAGE + [3, 0x04]
            response, sw1, sw2 = connection.transmit(cc_cmd)
            if sw1 == 0x90:
                self.log_signal.emit("Debug", f"CC: {self.toHexString(response)}")
            else:
                self.log_signal.emit("Error", f"CC read failed: SW1={sw1:02X} SW2={sw2:02X}")
                return []
        except Exception as e:
            self.log_signal.emit("Error", f"CC read error: {str(e)}")
            return []
            
        # NTAG213 has pages 4-39 available for user data
        for page in range(4, 40):
            try:
                read_cmd = self.READ_PAGE + [page, 0x04]  # Read 4 bytes
                response, sw1, sw2 = connection.transmit(read_cmd)
                
                if sw1 == 0x90:
                    all_data.extend(response)
                    self.log_signal.emit("Debug", f"Page {page}: {self.toHexString(response)}")
                else:
                    self.log_signal.emit("Debug", f"Read stopped at page {page}: SW1={sw1:02X} SW2={sw2:02X}")
                    break
                    
                # Check for end of NDEF message
                if len(response) >= 4 and response[0] == 0xFE:
                    self.log_signal.emit("Debug", "Found NDEF terminator, stopping read")
                    break
                    
            except Exception as e:
                self.log_signal.emit("Error", f"Error reading page {page}: {str(e)}")
                break
                
        if not all_data:
            self.log_signal.emit("Error", "No data read from tag")
            
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
            self.log_signal.emit("System", f"Started scanning for tags (will timeout after {self.scan_timeout} seconds of inactivity)")
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
        self.last_activity_time = time.time()
        
        while self.scanning:
            # Check for timeout
            if time.time() - self.last_activity_time > self.scan_timeout:
                self.log_signal.emit("System", f"Scanning stopped after {self.scan_timeout} seconds of inactivity")
                self.scanning = False
                # Update UI from main thread
                self.status_signal.emit("Status: Scanning timed out - No recent activity")
                break
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
                            self.last_activity_time = time.time()  # Update activity timestamp
                            self.log_signal.emit("New tag detected", f"UID: {uid}")
                            self.update_tag_status(True)  # Update status when tag detected
                            
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
                self.update_tag_status(False)  # Update status when tag is removed/error
                
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
            while current_pos < len(data) - 1:  # Ensure we can read length byte
                tlv_type = data[current_pos]
                
                # Skip null bytes that might appear before valid TLV blocks
                if tlv_type == 0x00:
                    current_pos += 1
                    continue
                    
                if tlv_type == 0xFE:  # Terminator TLV
                    break
                
                # Validate we can read the length byte
                if current_pos + 1 >= len(data):
                    self.log_signal.emit("Debug", "Incomplete TLV structure - missing length byte")
                    break
                
                # Get length for TLV types
                length = data[current_pos + 1]
                current_pos += 2  # Skip type and length bytes
                
                # Validate we have enough data for the TLV value
                if current_pos + length > len(data):
                    self.log_signal.emit("Debug", f"Incomplete TLV value - expected {length} bytes but only {len(data) - current_pos} available")
                    break
                
                # Process NDEF message (type 0x03) or Capability Container (type 0x01)
                if tlv_type == 0x03 or (tlv_type == 0x01 and length > 0):  # NDEF TLV or CC
                    self.log_signal.emit("Debug", f"TLV type 0x{tlv_type:02X} found, length: {length} bytes")
                    self.log_signal.emit("Debug", f"Total data available: {len(data)} bytes")
                    
                    # Skip CC and look for NDEF message if this is a CC TLV
                    if tlv_type == 0x01:
                        current_pos += length
                        continue
                    
                    # Ensure we have enough data for the NDEF record header
                    if current_pos + 3 > len(data):  # Minimum NDEF header size
                        self.log_signal.emit("Debug", "Incomplete NDEF record header")
                        break
                        
                    try:
                        # Validate minimum record size
                        if current_pos + 3 > len(data):
                            self.log_signal.emit("Debug", "Record too short for NDEF header")
                            break
                            
                        # Parse NDEF record header
                        flags = data[current_pos]  # Record header flags
                        tnf = flags & 0x07  # Type Name Format (last 3 bits)
                        is_first = (flags & 0x80) != 0  # MB (Message Begin)
                        is_last = (flags & 0x40) != 0   # ME (Message End)
                        cf_flag = (flags & 0x20) != 0   # CF (Chunk Flag)
                        sr_flag = (flags & 0x10) != 0   # SR (Short Record)
                        il_flag = (flags & 0x08) != 0   # IL (ID Length present)
                        
                        # Validate TNF and flags
                        if tnf not in [0x01, 0x02, 0x03, 0x04, 0x05, 0x06]:  # Valid TNF values
                            self.log_signal.emit("Debug", f"Invalid TNF value: {tnf}")
                            break
                            
                        if not is_first and current_pos == 0:  # First record must have MB flag
                            self.log_signal.emit("Debug", "First record missing MB flag")
                            break
                            
                        if cf_flag:  # We don't support chunked records
                            self.log_signal.emit("Debug", "Chunked records are not supported")
                            break
                            
                        if not sr_flag:  # We only support short records
                            self.log_signal.emit("Debug", "Only short records are supported")
                            break
                            
                        # Get record lengths
                        type_length = data[current_pos + 1]  # Length of the type field
                        payload_length = data[current_pos + 2]  # Length of the payload
                        
                        # Validate record size after getting lengths
                        if type_length == 0:
                            self.log_signal.emit("Debug", "Empty record type")
                            break
                            
                        if payload_length == 0:
                            self.log_signal.emit("Debug", "Empty payload")
                            break
                        
                        # Validate we have enough data for the complete record
                        header_size = 3 + type_length  # Basic header + type field
                        if il_flag:
                            if current_pos + header_size >= len(data):
                                self.log_signal.emit("Debug", "Missing ID length field")
                                break
                            id_length = data[current_pos + header_size]
                            header_size += 1 + id_length
                            
                        if current_pos + header_size + payload_length > len(data):
                            self.log_signal.emit("Debug", "Incomplete NDEF record payload")
                            break
                            
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

                            # Validate payload length before accessing
                            if offset >= len(data) or offset + payload_length > len(data):
                                self.log_signal.emit("Error", "Invalid payload length in NDEF record")
                                return
                            
                            try:
                                # Get the URL content first
                                url_content = bytes(content_bytes).decode('utf-8', errors='replace')
                                self.log_signal.emit("Debug", f"URL content before prefix: {url_content}")
                            except Exception as e:
                                self.log_signal.emit("Error", f"Failed to decode URL content: {str(e)}")
                                return
                            
                            # Enhanced URL detection with more comprehensive patterns and validation
                            looks_like_web = url_content and any([
                                # Standard URL patterns
                                url_content.startswith(("www.", "http:", "https:")),
                                
                                # Common domain patterns
                                any(url_content.startswith(domain) for domain in [
                                    "github.com",
                                    "gitlab.com",
                                    "bitbucket.org",
                                    "homebox.",
                                    "box.",
                                    "docs.",
                                    "drive.",
                                    "cloud.",
                                    "app.",
                                    "api.",
                                    "portal.",
                                    "dashboard.",
                                    "login.",
                                    "auth.",
                                    "account."
                                ]),
                                
                                # TLD detection
                                any("." + tld in url_content.lower() for tld in [
                                    # Generic TLDs
                                    "com", "org", "net", "edu", "gov", "mil", "int",
                                    # Common country TLDs
                                    "uk", "us", "eu", "ca", "au", "de", "fr", "jp",
                                    # Tech TLDs
                                    "io", "app", "dev", "tech", "cloud", "ai",
                                    # Business TLDs
                                    "biz", "info", "co", "me", "pro"
                                ]),
                                
                                # IP address pattern (basic check)
                                bool(re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?(/.*)?$', url_content))
                            ])
                            
                            # Determine URL prefix with enhanced logic and validation
                            original_prefix = url_prefixes.get(url_prefix_byte, "")
                            if url_prefix_byte not in url_prefixes:
                                self.log_signal.emit("Debug", f"Unknown URL prefix byte: 0x{url_prefix_byte:02X}")
                            
                            # Handle special cases
                            if looks_like_web:
                                if original_prefix in ["tel:", "mailto:", ""]:
                                    # Override non-web prefixes for web-like content
                                    if url_content.startswith(("https:", "http:")):
                                        # Keep explicit protocol if present
                                        prefix = ""
                                    elif url_content.startswith("www."):
                                        prefix = "http://"  # Default to http:// for www
                                    else:
                                        prefix = "https://"  # Default to https:// for modern web
                                    self.log_signal.emit("Debug", f"Using web prefix {prefix} for web-like URL")
                                else:
                                    # Keep valid web prefix
                                    prefix = original_prefix
                                    self.log_signal.emit("Debug", f"Using original web prefix: {prefix}")
                            else:
                                if original_prefix:
                                    # Keep valid non-web prefix
                                    prefix = original_prefix
                                    self.log_signal.emit("Debug", f"Using original non-web prefix: {prefix}")
                                else:
                                    # Default to text record if no valid prefix
                                    self.log_signal.emit("Debug", f"Invalid prefix byte: 0x{url_prefix_byte:02X}, treating as text")
                                    return
                            
                            # Construct and validate full URL
                            if not url_content:
                                self.log_signal.emit("Error", "Empty URL content")
                                return
                                
                            url = prefix + url_content
                            
                            # Basic URL validation and LAN IP handling
                            if not any(url.startswith(p) for p in ["http://", "https://", "tel:", "mailto:"]):
                                self.log_signal.emit("Debug", f"Invalid URL format: {url}")
                                if looks_like_web:
                                    url = "https://" + url_content

                            # Check if URL is a LAN IP address and rewrite https:// to http://
                            lan_ip_pattern = re.compile(r'^https://(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)')
                            if lan_ip_pattern.match(url):
                                url = 'http://' + url[8:]  # Replace https:// with http://
                                self.log_signal.emit("Debug", f"Rewrote LAN IP URL to: {url}")
                            
                            # Additional validation for tel: URLs
                            if url.startswith("tel:") and not url_content.replace("+","").replace("-","").replace(".","").isdigit():
                                self.log_signal.emit("Debug", "Converting invalid tel: URL to http://")
                                url = "http://" + url_content
                            self.log_signal.emit("URL Detected", f"Found URL: {url}")
                            self.url_signal.emit(url)
                            
                            # Try to open URL in Chrome
                            if url.startswith(("http://", "https://")):
                                # Try to open in browser without reachability check
                                try:
                                    # Try google-chrome first with timeout
                                    process = subprocess.Popen(['google-chrome', url], 
                                                            start_new_session=True)
                                    try:
                                        process.wait(timeout=3)
                                        self.log_signal.emit("System", "Opening URL in Chrome")
                                    except subprocess.TimeoutExpired:
                                        # Process started but didn't exit - this is normal
                                        self.log_signal.emit("System", "Opening URL in Chrome")
                                except FileNotFoundError:
                                    try:
                                        # Fallback to chrome if google-chrome not found
                                        process = subprocess.Popen(['chrome', url], 
                                                                start_new_session=True)
                                        try:
                                            process.wait(timeout=3)
                                            self.log_signal.emit("System", "Opening URL in Chrome")
                                        except subprocess.TimeoutExpired:
                                            self.log_signal.emit("System", "Opening URL in Chrome")
                                    except FileNotFoundError:
                                        # Last resort fallback to xdg-open
                                        try:
                                            process = subprocess.Popen(['xdg-open', url], 
                                                                    start_new_session=True)
                                            try:
                                                process.wait(timeout=3)
                                                self.log_signal.emit("System", "Opening URL in default browser")
                                            except subprocess.TimeoutExpired:
                                                self.log_signal.emit("System", "Opening URL in default browser")
                                        except Exception as e:
                                            self.log_signal.emit("Error", f"Failed to open URL: {str(e)}")
                                except Exception as e:
                                    self.log_signal.emit("Error", f"Failed to launch Chrome: {str(e)}")
                                except (urllib.error.URLError, ssl.SSLError) as e:
                                    self.log_signal.emit("Error", f"URL not reachable: {str(e)}")
                                except Exception as e:
                                    self.log_signal.emit("Error", f"Failed to verify URL: {str(e)}")
                            
                            # Handle special URL types
                            if url.startswith("tel:"):
                                if not url_content.replace("+","").replace("-","").replace(".","").isdigit():
                                    url = "http://" + url_content
                            elif url.startswith("mailto:"):
                                if not re.match(r'^[^@]+@[^@]+\.[^@]+$', url_content):
                                    url = "http://" + url_content
                            
                            # Update URL label and try to open web URLs
                            self.url_signal.emit(url)
                        elif record_type_bytes == b'T' or (len(record_type) == 1 and record_type[0] == 0x54):  # Text Record
                            # First byte contains text info
                            text_info = data[offset]
                            lang_code_length = text_info & 0x3F  # Lower 6 bits
                            content_start = offset + 1 + lang_code_length
                            content_bytes = data[content_start:content_start+payload_length-1-lang_code_length]  # -1 for status byte
                            
                            text = bytes(content_bytes).decode('utf-8')
                            self.log_signal.emit("Text Record", f"Content: {text}")
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
            self.log_text.clear()
            self.log_signal.emit("System", "Debug mode disabled")
        else:
            self.log_signal.emit("System", "Debug mode enabled")

    def append_log(self, title, message):
        """Append formatted message to log."""
        # Only show debug messages if debug mode is enabled
        if title == "Debug" and not self.debug_mode:
            return
            
        # Only show important messages by default
        if not self.debug_mode and title not in ["Error", "URL Detected", "System", "Text Record"]:
            return
            
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        formatted_msg = f'<div style="font-family: Segoe UI"><span style="color: #666666">[{timestamp}]</span> <span style="color: {self._get_title_color(title)}">[{title}]</span> {message}</div>'
        
        self.log_text.append(formatted_msg)
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
            QMessageBox.critical(self, "Error", "Please enter a URL to write to the tag")
            return
            
        # Enhanced validation to prevent accidental writes
        if not any(text.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
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
                self.write_entry.setText(text)
                self.validate_write_input()
            else:
                return
            
        # Validate that input is a URL
        if not any(text.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
            QMessageBox.critical(self, "Error", "Only URLs are allowed. Please enter a valid URL starting with http://, https://, or www.")
            return
            
        # Validate URL format if it looks like a URL
        if any(text.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
            try:
                if not text.startswith(('http://', 'https://')):
                    text = 'https://' + text.lstrip('www.')
                                    
                # Check if URL is a LAN IP and rewrite https:// to http://
                lan_ip_pattern = re.compile(r'^https://(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)')
                if lan_ip_pattern.match(text):
                    text = 'http://' + text[8:]  # Replace https:// with http://
                    self.log_signal.emit("Debug", f"Rewrote LAN IP URL to: {text}")
                                    
                # Basic URL validation
                if not re.match(r'^https?://[^\s/$.?#].[^\s]*$', text):
                    raise ValueError("Invalid URL format")
                self.write_entry.setText(text)  # Update with normalized URL
            except ValueError:
                QMessageBox.warning(self, "Warning", "The URL format appears to be invalid. Please check and try again.")
                return
            
        quantity = self.quantity_spinbox.value()
        if quantity < 1:
            QMessageBox.critical(self, "Error", "Quantity must be at least 1")
            return
            
        self.write_status.setText("Ready - Please present first tag...")
        self.progress_label.setText(f"Starting batch operation: 0/{quantity} tags written")
        
        threading.Thread(target=self.batch_write_tags, 
                       args=(text, quantity), 
                       daemon=True).start()

    def paste_to_write_entry(self):
        """Paste clipboard content into write entry."""
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            # Store original text for comparison
            original_text = text
            
            # Try to normalize URL format
            if text.startswith('www.'):
                text = 'https://' + text
            elif not text.startswith(('http://', 'https://')):
                # Check if it looks like a domain
                if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text):
                    text = 'https://' + text
            
            self.write_entry.setText(text)
            self.validate_write_input()
            
            # Show notification with the new URL
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setWindowTitle("URL Updated")
            
            if text != original_text:
                msg.setText(f"URL normalized and updated:\n{text}")
                msg.setInformativeText(f"Original text: {original_text}")
            else:
                msg.setText(f"URL updated:\n{text}")
            
            # Style the message box
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QPushButton {
                    padding: 6px 20px;
                    background-color: #1976d2;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #1565c0;
                }
            """)
            
            # Auto-close after 2 seconds
            QTimer.singleShot(2000, msg.close)
            msg.show()
            
            # Also log the change
            self.log_signal.emit("System", f"URL updated to: {text}")

    def clear_write_entry(self):
        """Clear the write entry field."""
        self.write_entry.clear()
        self.url_preview.clear()
        self.validation_label.clear()
        self.char_count_label.setText("Characters remaining: 137")
        self.validate_write_input()
        
    def test_url(self):
        """Test the URL by opening it in the default browser."""
        url = self.write_entry.text().strip()
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url.lstrip('www.')
            try:
                # Try google-chrome first
                subprocess.Popen(['google-chrome', url], start_new_session=True)
                self.log_signal.emit("System", "Testing URL in Chrome")
            except FileNotFoundError:
                try:
                    # Fallback to chrome if google-chrome not found
                    subprocess.Popen(['chrome', url], start_new_session=True)
                    self.log_signal.emit("System", "Testing URL in Chrome")
                except FileNotFoundError:
                    # Last resort fallback to xdg-open
                    try:
                        subprocess.Popen(['xdg-open', url], start_new_session=True)
                        self.log_signal.emit("System", "Testing URL in default browser")
                    except Exception as e:
                        self.log_signal.emit("Error", f"Failed to test URL: {str(e)}")
            except Exception as e:
                self.log_signal.emit("Error", f"Failed to test URL in Chrome: {str(e)}")

    def validate_write_input(self):
        """Validate URL input and provide feedback."""
        text = self.write_entry.text().strip()
        
        # Enable/disable quick write button along with main write button
        self.quick_write_button.setEnabled(False)
        
        # Update character count with more visible feedback
        remaining = 137 - len(text)  # NTAG213 URL capacity
        if remaining < 0:
            self.char_count_label.setStyleSheet("""
                color: #F44336;
                font-weight: bold;
                background-color: #FFEBEE;
                padding: 4px 8px;
                border-radius: 4px;
            """)
        elif remaining < 20:
            self.char_count_label.setStyleSheet("""
                color: #FF9800;
                font-weight: bold;
                background-color: #FFF3E0;
                padding: 4px 8px;
                border-radius: 4px;
            """)
        else:
            self.char_count_label.setStyleSheet("""
                color: #666666;
                padding: 4px 8px;
            """)
        self.char_count_label.setText(f"Characters remaining: {remaining}")
        
        # Enhanced URL validation
        if text:
            # Check for valid URL format
            url_valid = False
            if any(text.startswith(prefix) for prefix in ['http://', 'https://', 'www.']):
                try:
                    # Normalize URL format
                    if text.startswith('www.'):
                        text = 'https://' + text
                    
                    # Basic URL validation regex
                    url_pattern = re.compile(
                        r'^https?://'  # http:// or https://
                        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                        r'localhost|'  # localhost...
                        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                        r'(?::\d+)?'  # optional port
                        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                    
                    url_valid = bool(url_pattern.match(text))
                except Exception:
                    url_valid = False
                
            # Additional validation for inventory system URLs
            inventory_valid = bool(re.match(r'^https?://inventory\.example\.com/item/[\w-]+$', text))
            
            if url_valid:
                self.write_button.setEnabled(True)
                self.quick_write_button.setEnabled(True)
                
                if inventory_valid:
                    self.validation_label.setStyleSheet("""
                        color: #4CAF50;
                        font-weight: bold;
                        background-color: #E8F5E9;
                        padding: 4px 8px;
                        border-radius: 4px;
                    """)
                    self.validation_label.setText("✓ Valid Inventory System URL")
                else:
                    self.validation_label.setStyleSheet("""
                        color: #FF9800;
                        font-weight: bold;
                        background-color: #FFF3E0;
                        padding: 4px 8px;
                        border-radius: 4px;
                    """)
                    self.validation_label.setText("✓ Valid URL format (Non-inventory URL)")
                self.validation_label.setStyleSheet("""
                    color: #4CAF50;
                    font-weight: bold;
                    background-color: #E8F5E9;
                    padding: 4px 8px;
                    border-radius: 4px;
                """)
                self.validation_label.setText("✓ Valid URL format")
            else:
                self.write_button.setEnabled(False)
                self.validation_label.setStyleSheet("""
                    color: #F44336;
                    font-weight: bold;
                    background-color: #FFEBEE;
                    padding: 4px 8px;
                    border-radius: 4px;
                """)
                self.validation_label.setText("✗ Invalid URL format - Must start with http://, https://, or www.")
        else:
            self.write_button.setEnabled(False)
            self.validation_label.setText("")
            self.validation_label.setStyleSheet("")
        
        # Disable write button if text is too long
        if remaining < 0:
            self.write_button.setEnabled(False)

    def show_write_success(self):
        """Show a temporary success animation."""
        success_label = QLabel("✓", self)
        success_label.setStyleSheet("""
            QLabel {
                color: white;
                background-color: #4CAF50;
                border-radius: 25px;
                padding: 15px;
                font-size: 24px;
            }
        """)
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_label.setFixedSize(50, 50)
        
        # Position in center of window
        success_label.move(
            self.width() // 2 - success_label.width() // 2,
            self.height() // 2 - success_label.height() // 2
        )
        
        success_label.show()
        
        # Fade out animation
        def fade_out():
            success_label.setStyleSheet("""
                QLabel {
                    color: transparent;
                    background-color: transparent;
                    border-radius: 25px;
                    padding: 15px;
                    font-size: 24px;
                }
            """)
            QTimer.singleShot(200, success_label.deleteLater)
            
        QTimer.singleShot(500, fade_out)

    def update_tag_status(self, detected: bool, locked: bool = False):
        """Update the tag status indicator and label."""
        if detected:
            if locked:
                self.tag_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 7px;")  # Green
                self.tag_status_label.setText("Tag Detected & Locked ✓")
            else:
                self.tag_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 7px;")  # Green
                self.tag_status_label.setText("Tag Detected")
        else:
            self.tag_indicator.setStyleSheet("background-color: #FFA500; border-radius: 7px;")  # Orange
            self.tag_status_label.setText("No Tag Present")


    def batch_write_tags(self, text: str, quantity: int):
        """Write the same data to multiple tags."""
        tags_written = 0
        last_uid = None
        
        while tags_written < quantity:
            self.update_tag_status(False)  # Reset status when waiting for new tag
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
                        self.update_tag_status(True)  # Update status when tag detected
                        self.write_status_signal.emit(f"Write to tag {uid}...")
                        
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
                        
                        # Store URL in recent list if not already present
                        if text not in self.recent_urls:
                            self.recent_urls.insert(0, text)
                            self.recent_urls = self.recent_urls[:10]  # Keep last 10
                            self.url_combo.clear()
                            self.url_combo.addItems(self.recent_urls)
                        
                        # Show success animation
                        self.show_write_success()
                        
                        self.progress_signal.emit(
                            f"Progress: {tags_written}/{quantity} tags written")
                        
                        if tags_written == quantity:
                            self.write_status_signal.emit(
                                f"Successfully wrote {quantity} tags")
                            if self.lock_checkbox.isChecked():
                                self.update_tag_status(True, True)  # Show locked status
                            break
                        else:
                            if self.lock_checkbox.isChecked():
                                self.update_tag_status(True, True)  # Show locked status
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
