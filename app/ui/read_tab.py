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
        layout.setSpacing(5)  # Reduced spacing between major sections
        layout.setContentsMargins(5, 5, 5, 5)  # Minimal padding around the entire tab
        
        # Status section with modern card-like design
        # Simplified status label with better compact view support
        self.status_label = QLabel("Status: Waiting for reader...")
        self.status_label.setObjectName("status_label")
        self.status_label.setMinimumHeight(20)  # Reduced minimum height
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Scan button
        self.scan_button = QPushButton("Start Scanning")
        self.scan_button.clicked.connect(self._on_scan_button_clicked)
        # Use minimum width instead of fixed width for better scaling
        self.scan_button.setMinimumWidth(120)
        self.scan_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.scan_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # URL Detection group
        url_group = QGroupBox("Detected URL")
        url_group.setContentsMargins(5, 5, 5, 5)  # Reduced padding
        url_layout = QHBoxLayout(url_group)
        self.url_label = QLabel("")
        self.url_label.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 11px;
                color: #1976D2;
                padding: 4px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: #f5f5f5;
                min-height: 25px;
            }
        """)
        self.url_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.url_label.setWordWrap(True)
        self.url_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.url_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        url_layout.addWidget(self.url_label)
        
        # Add copy button for URL
        self.copy_url_button = QPushButton("Copy")
        self.copy_url_button.setToolTip("Copy URL to clipboard")
        self.copy_url_button.setMinimumWidth(80)
        self.copy_url_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.copy_url_button.clicked.connect(self._on_copy_url_clicked)
        self.copy_url_button.setEnabled(False)  # Disabled by default
        url_layout.addWidget(self.copy_url_button)
        
        layout.addWidget(url_group)
        
        # Log group with debug toggle
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(5, 5, 5, 5)  # Reduced padding
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.3;
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        self.log_text.setMinimumHeight(100)  # Reduced minimum height for log area
        log_layout.addWidget(self.log_text)
        
        # Log controls
        log_controls = QHBoxLayout()
        log_controls.setSpacing(8)  # Reduced spacing
        
        self.copy_log_button = QPushButton("Copy Log")
        self.copy_log_button.clicked.connect(self._on_copy_log_clicked)
        self.copy_log_button.setMinimumWidth(80)
        self.copy_log_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        
        self.clear_log_button = QPushButton("Clear Log")
        self.clear_log_button.clicked.connect(self._on_clear_log_clicked)
        self.clear_log_button.setMinimumWidth(80)
        self.clear_log_button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        
        self.debug_checkbox = QCheckBox("Debug Mode")
        self.debug_checkbox.setToolTip("Show detailed debug information in the log")
        self.debug_checkbox.toggled.connect(self._on_debug_toggled)
        
        log_controls.addWidget(self.copy_log_button)
        log_controls.addWidget(self.clear_log_button)
        log_controls.addStretch()
        log_controls.addWidget(self.debug_checkbox)
        
        log_layout.addLayout(log_controls)
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