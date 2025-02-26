"""
Read Tab UI components for the NFC Reader/Writer application.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QCheckBox, QGroupBox,
                            QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ReadTab(QWidget):
    """Read Tab UI component."""
    
    # Signals
    scan_toggled = pyqtSignal(bool)
    copy_log_clicked = pyqtSignal()
    clear_log_clicked = pyqtSignal()
    copy_url_clicked = pyqtSignal()
    debug_toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        """Initialize the Read Tab UI."""
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the read tab interface."""
        layout = QVBoxLayout(self)
        
        # Status section with modern card-like design
        # Simplified status label with better compact view support
        self.status_label = QLabel("Status: Waiting for reader...")
        self.status_label.setObjectName("status_label")
        self.status_label.setMinimumHeight(20)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Scan button
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.clicked.connect(self._on_scan_button_clicked)
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
        self.copy_url_button.clicked.connect(self._on_copy_url_clicked)
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
        self.debug_checkbox.stateChanged.connect(self._on_debug_toggled)
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
        self.copy_button.clicked.connect(self._on_copy_log_clicked)
        self.copy_button.setToolTip("Copy log contents to clipboard")
        self.copy_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        self.clear_button = QPushButton("🗑️ Clear Log")
        self.clear_button.clicked.connect(self._on_clear_log_clicked)
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
    
    def _on_scan_button_clicked(self):
        """Handle scan button click."""
        is_scanning = self.scan_button.text() == "Stop Scanning"
        if is_scanning:
            self.scan_button.setText("Start Scanning")
            self.scan_button.setStyleSheet("")  # Reset to default style
        else:
            self.scan_button.setText("Stop Scanning")
            self.scan_button.setStyleSheet("background-color: #c62828;")  # Red for stop
        
        self.scan_toggled.emit(not is_scanning)
    
    def _on_copy_log_clicked(self):
        """Handle copy log button click."""
        self.copy_log_clicked.emit()
    
    def _on_clear_log_clicked(self):
        """Handle clear log button click."""
        self.clear_log_clicked.emit()
    
    def _on_copy_url_clicked(self):
        """Handle copy URL button click."""
        self.copy_url_clicked.emit()
    
    def _on_debug_toggled(self, state):
        """Handle debug mode toggle."""
        self.debug_toggled.emit(bool(state))
    
    def update_status(self, text):
        """Update the status label."""
        self.status_label.setText(text)
    
    def update_url(self, text):
        """Update the URL label."""
        self.url_label.setText(text)
    
    def append_log(self, title, message, timestamp, title_color):
        """Append formatted message to log."""
        formatted_msg = f'<div style="font-family: Segoe UI"><span style="color: #666666">[{timestamp}]</span> <span style="color: {title_color}">[{title}]</span> {message}</div>'
        
        self.log_text.append(formatted_msg)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def clear_log(self):
        """Clear the log text."""
        self.log_text.clear()
    
    def get_log_text(self):
        """Get the log text content."""
        return self.log_text.toPlainText()