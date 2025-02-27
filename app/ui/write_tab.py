"""
Write Tab UI components for the NFC Reader/Writer application.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QLineEdit, QSpinBox, QCheckBox, 
                            QGroupBox, QSizePolicy, QComboBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class WriteTab(QWidget):
    """Write Tab UI component."""
    
    # Signals
    write_clicked = pyqtSignal()
    paste_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()
    test_url_clicked = pyqtSignal()
    clear_status_clicked = pyqtSignal()
    text_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """Initialize the Write Tab UI."""
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the write tab interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Consistent spacing between major sections
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
        input_container_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins for better spacing
        input_container_layout.setSpacing(8)  # Consistent spacing between elements
        
        # Recent URLs dropdown
        self.url_combo = QComboBox()
        self.url_combo.setMinimumWidth(300)  # Ensure minimum readable width
        self.url_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # Allow expanding horizontally
        self.url_combo.setMinimumHeight(45)  # Taller for better touch targets
        self.url_combo.setEditable(True)
        self.url_combo.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.url_combo.currentTextChanged.connect(self._on_text_changed)
        self.write_entry = self.url_combo.lineEdit()
        self.write_entry.setStyleSheet("""
            QLineEdit {
                font-family: 'Segoe UI';
                font-size: 14px;  /* Slightly smaller font */
                padding: 8px;  /* Reduced padding */
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                margin-bottom: 10px;  /* Reduced margin */
                margin-top: 5px;
                min-width: 300px;  /* Ensure minimum readable width */
            }
            QLineEdit:focus {
                border: 2px solid #1976d2;
                background-color: #f5f5f5;
            }
            QLineEdit::placeholder {
                color: #9e9e9e;
            }
        """)
        
        # Paste button with circular icon style
        paste_tooltip = "Paste URL from clipboard (Ctrl+V)"
        paste_button = QPushButton("📋")
        paste_button.setToolTip(paste_tooltip)
        paste_button.clicked.connect(self._on_paste_clicked)
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
        clear_tooltip = "Clear input field (Ctrl+L)"
        clear_button = QPushButton("🗑️")
        clear_button.setToolTip(clear_tooltip)
        clear_button.clicked.connect(self._on_clear_clicked)
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
        input_container_layout.addWidget(paste_button, alignment=Qt.AlignmentFlag.AlignRight)
        input_container_layout.addWidget(clear_button)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(input_container)
        input_layout.addWidget(self.validation_label)
        input_layout.addWidget(self.char_count_label)
        
        # Add test URL button next to input
        test_url_button = QPushButton("🔗 Test URL")
        test_url_button.setToolTip("Open URL in browser to test")
        test_url_button.clicked.connect(self._on_test_url_clicked)
        test_url_button.setFixedWidth(100)
        input_container_layout.addWidget(test_url_button)
        
        # Batch writing section
        batch_widget = QWidget()
        batch_layout = QHBoxLayout(batch_widget)
        batch_layout.setContentsMargins(0, 10, 0, 0)  # Add top padding for separation
        
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
        options_layout.setContentsMargins(15, 15, 15, 15)  # Consistent padding
        self.lock_checkbox = QCheckBox("Lock tag after writing")
        self.lock_checkbox.setChecked(True)
        options_layout.addWidget(self.lock_checkbox)
        
        self.write_button = QPushButton("Write Tag")
        self.write_button.clicked.connect(self._on_write_clicked)
        self.write_button.setFixedWidth(180)
        self.write_button.setEnabled(False)  # Disabled by default
        
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
        status_layout.setSpacing(16)  # Consistent spacing

        # Progress section with label and progress bar
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)  # Tight spacing between label and bar
        
        self.progress_label = QLabel("Ready")
        progress_layout.addWidget(self.progress_label)
        
        # Add progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        status_layout.addWidget(progress_widget)
        
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
        self.clear_status_button.clicked.connect(self._on_clear_status_clicked)
        write_status_layout.addWidget(self.clear_status_button)
        
        status_layout.addWidget(tag_status_widget)
        layout.addWidget(status_group)
        layout.addStretch()
    
    def _on_write_clicked(self):
        """Handle write button click."""
        self.write_clicked.emit()
    
    def _on_paste_clicked(self):
        """Handle paste button click."""
        self.paste_clicked.emit()
    
    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.clear_clicked.emit()
    
    def _on_test_url_clicked(self):
        """Handle test URL button click."""
        self.test_url_clicked.emit()
    
    def _on_clear_status_clicked(self):
        """Handle clear status button click."""
        self.clear_status_clicked.emit()
    
    def _on_text_changed(self, text):
        """Handle text changed in the URL field."""
        self.text_changed.emit(text)
    
    def update_validation(self, is_valid, message):
        """Update the validation label."""
        try:
            if is_valid:
                self.validation_label.setStyleSheet("color: green; margin-top: 5px;")
                self.validation_label.setText("✓ " + message)
            else:
                self.validation_label.setStyleSheet("color: red; margin-top: 5px;")
                self.validation_label.setText("✗ " + message)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def update_char_count(self, remaining):
        """Update the character count label."""
        try:
            if remaining < 0:
                self.char_count_label.setStyleSheet("color: red; margin-top: 5px;")
                self.char_count_label.setText(f"Characters over limit: {abs(remaining)}")
            else:
                self.char_count_label.setStyleSheet("color: #666666; margin-top: 5px;")
                self.char_count_label.setText(f"Characters remaining: {remaining}")
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def update_write_button(self, enabled):
        """Update the write button state."""
        try:
            self.write_button.setEnabled(enabled)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def update_tag_status(self, detected, locked=False):
        """Update the tag status indicator."""
        try:
            if detected:
                self.tag_indicator.setStyleSheet("background-color: green; border-radius: 10px;")
                self.tag_status_label.setText("Tag Detected" + (" (Locked)" if locked else ""))
            else:
                self.tag_indicator.setStyleSheet("background-color: red; border-radius: 10px;")
                self.tag_status_label.setText("No Tag Detected")
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def update_write_status(self, text):
        """Update the write status label."""
        try:
            self.write_status.setText(text)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def update_progress(self, text):
        """Update the progress label."""
        try:
            self.progress_label.setText(text)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
        
    def update_progress_bar(self, current, total):
        """Update the progress bar with current progress."""
        try:
            if total <= 0:
                self.progress_bar.setValue(0)
                return
                
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        except RuntimeError:
            # Ignore errors if the UI element has been deleted
            pass
    
    def get_url(self):
        """Get the current URL text."""
        return self.write_entry.text().strip()
    
    def set_url(self, text):
        """Set the URL text."""
        self.write_entry.setText(text)
    
    def get_quantity(self):
        """Get the quantity value."""
        return self.quantity_spinbox.value()
    
    def get_lock_state(self):
        """Get the lock checkbox state."""
        return self.lock_checkbox.isChecked()
    
    def add_recent_url(self, url):
        """Add a URL to the recent URLs list."""
        # Check if URL is already in the list
        index = self.url_combo.findText(url)
        if index >= 0:
            self.url_combo.removeItem(index)
        
        # Add to the top of the list
        self.url_combo.insertItem(0, url)
        self.url_combo.setCurrentIndex(0)
        
        # Keep only the last 10 items
        while self.url_combo.count() > 10:
            self.url_combo.removeItem(self.url_combo.count() - 1)