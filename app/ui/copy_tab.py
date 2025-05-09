"""
Copy Tab UI components for the NFC Reader/Writer application.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSpinBox, QCheckBox, QGroupBox,
                            QSizePolicy, QGridLayout, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class CopyTab(QWidget):
    """Copy Tab UI component."""
    
    # Signals
    read_source_clicked = pyqtSignal()
    copy_clicked = pyqtSignal()
    reset_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the Copy Tab UI."""
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the copy tab interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)  # Reduced spacing between major sections
        layout.setContentsMargins(5, 5, 5, 5)  # Minimal padding around the entire tab
        
        # Status section
        self.copy_status_label = QLabel("Status: Waiting for reader...")
        self.copy_status_label.setObjectName("status_label")
        self.copy_status_label.setMinimumHeight(20)
        self.copy_status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.copy_status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.copy_status_label.setWordWrap(True)
        layout.addWidget(self.copy_status_label)
        
        # Source tag section
        source_group = QGroupBox("Source Tag")
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(5, 5, 5, 5)  # Reduced padding
        # Source tag info with improved display for long URLs
        source_layout.addWidget(QLabel("Source Tag Content:"))
        self.source_tag_info = QLabel("No source tag scanned yet")
        self.source_tag_info.setStyleSheet("""
            QLabel {
                font-family: 'Segoe UI';
                font-size: 11px;
                color: #1976D2;
                padding: 4px;
                background-color: #E3F2FD;
                border-radius: 3px; 
                min-height: 30px;
            }
        """)
        self.source_tag_info.setWordWrap(True)
        source_layout.addWidget(self.source_tag_info)
        
        # Read source tag button
        self.read_source_button = QPushButton("Read & Store Tag")
        self.read_source_button.clicked.connect(self._on_read_source_clicked)
        self.read_source_button.setMinimumWidth(100)
        self.read_source_button.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        source_layout.addWidget(self.read_source_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(source_group)
        
        # Copy configuration section
        copy_config_group = QGroupBox("Copy Configuration")
        copy_config_layout = QVBoxLayout(copy_config_group)
        copy_config_layout.setContentsMargins(5, 5, 5, 5)  # Reduced padding
        # Number of copies
        # Use grid layout instead of horizontal layout for better responsiveness
        copies_grid = QGridLayout()
        copies_grid.setContentsMargins(0, 0, 0, 0)
        
        copies_label = QLabel("Number of copies to make:")
        copies_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        copies_label.setWordWrap(True)
        self.copies_spinbox = QSpinBox()
        self.copies_spinbox.setRange(1, 10)
        self.copies_spinbox.setValue(1)
        self.copies_spinbox.setMinimumWidth(50)
        
        copies_grid.addWidget(copies_label, 0, 0)
        copies_grid.addWidget(self.copies_spinbox, 0, 1, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        copy_config_layout.addLayout(copies_grid)
        
        # Lock option
        self.copy_lock_checkbox = QCheckBox("Lock tags after writing")
        self.copy_lock_checkbox.setChecked(True)
        copy_config_layout.addWidget(self.copy_lock_checkbox)
        
        layout.addWidget(copy_config_group)
        
        # Copy operation section
        copy_op_group = QGroupBox("Copy Operation")
        copy_op_layout = QVBoxLayout(copy_op_group)
        copy_op_layout.setContentsMargins(5, 5, 5, 5)  # Reduced padding
        copy_op_layout.setSpacing(5)  # Reduced spacing
        
        # Progress section with label and progress bar
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(3)  # Tighter spacing between label and bar
        
        self.copy_progress_label = QLabel("Ready")
        progress_layout.addWidget(self.copy_progress_label)
        
        # Add progress bar
        self.copy_progress_bar = QProgressBar()
        self.copy_progress_bar.setRange(0, 100)
        self.copy_progress_bar.setValue(0)
        self.copy_progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.copy_progress_bar)
        
        button_grid = QGridLayout()
        button_grid.setContentsMargins(0, 5, 0, 0)
        button_grid.setSpacing(8)
        
        # Copy button
        self.copy_button = QPushButton("Copy to New Tag")
        self.copy_button.clicked.connect(self._on_copy_clicked)
        self.copy_button.setEnabled(False)  # Disabled until source tag is read
        self.copy_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.copy_button.setMinimumWidth(80)
        
        # Reset button
        self.reset_copy_button = QPushButton("Reset")
        self.reset_copy_button.clicked.connect(self._on_reset_clicked)
        self.reset_copy_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.reset_copy_button.setMinimumWidth(60)
        self.reset_copy_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        # Stop button
        self.stop_copy_button = QPushButton("Stop")
        self.stop_copy_button.clicked.connect(self._on_stop_clicked)
        self.stop_copy_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.stop_copy_button.setMinimumWidth(60)
        self.stop_copy_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.stop_copy_button.setEnabled(False)  # Disabled until copy operation starts
        
        # Add buttons to grid layout - will automatically wrap to new row when space is limited
        button_grid.addWidget(self.copy_button, 0, 0)
        button_grid.addWidget(self.reset_copy_button, 0, 1)
        button_grid.addWidget(self.stop_copy_button, 0, 2)
        
        # Set column stretch factors to ensure buttons resize properly
        button_grid.setColumnStretch(0, 2)  # Copy button gets more space
        button_grid.setColumnStretch(1, 1)
        button_grid.setColumnStretch(2, 1)
        
        copy_op_layout.addLayout(button_grid)
        
        # Tag status indicator
        tag_status_grid = QGridLayout()
        tag_status_grid.setContentsMargins(0, 0, 0, 0)
        tag_status_grid.setSpacing(8)
        
        self.copy_tag_indicator = QLabel()
        self.copy_tag_indicator.setFixedSize(15, 15)
        self.copy_tag_indicator.setStyleSheet("background-color: #FFA500; border-radius: 7px;")  # Orange by default
        
        self.copy_tag_status_label = QLabel("No Tag Present")
        self.copy_tag_status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.copy_tag_status_label.setWordWrap(True)
        tag_status_grid.addWidget(self.copy_tag_indicator, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        tag_status_grid.addWidget(self.copy_tag_status_label, 0, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        copy_op_layout.addWidget(progress_widget)
        copy_op_layout.addLayout(tag_status_grid)
        
        layout.addWidget(copy_op_group)
        layout.addStretch()
    
    def _on_read_source_clicked(self):
        """Handle read source button click."""
        self.read_source_clicked.emit()
    
    def _on_copy_clicked(self):
        """Handle copy button click."""
        self.copy_clicked.emit()
    
    def _on_reset_clicked(self):
        """Handle reset button click."""
        self.reset_clicked.emit()
    
    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.stop_clicked.emit()
    
    def update_status(self, text):
        """Update the status label."""
        self.copy_status_label.setText(text)
    
    def update_source_info(self, text):
        """Update the source tag info label."""
        self.source_tag_info.setText(text)
    
    def update_progress(self, text):
        """Update the progress label."""
        self.copy_progress_label.setText(text)
        
    def update_progress_bar(self, current, total):
        """Update the progress bar with current progress."""
        if total <= 0:
            self.copy_progress_bar.setValue(0)
            return
            
        percentage = int((current / total) * 100)
        self.copy_progress_bar.setValue(percentage)
    
    def update_tag_status(self, detected, locked=False):
        """Update the tag status indicator."""
        if detected:
            if locked:
                self.copy_tag_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 7px;")  # Green
                self.copy_tag_status_label.setText("Tag Detected & Locked ")
            else:
                self.copy_tag_indicator.setStyleSheet("background-color: #4CAF50; border-radius: 7px;")  # Green
                self.copy_tag_status_label.setText("Tag Detected")
        else:
            self.copy_tag_indicator.setStyleSheet("background-color: #FF9800; border-radius: 7px;")  # Orange for no tag
            self.copy_tag_status_label.setText("Waiting for Tag...")
    
    def enable_copy_button(self, enabled):
        """Enable or disable the copy button."""
        self.copy_button.setEnabled(enabled)
    
    def enable_stop_button(self, enabled):
        """Enable or disable the stop button."""
        self.stop_copy_button.setEnabled(enabled)
    
    def enable_read_button(self, enabled):
        """Enable or disable the read source button."""
        self.read_source_button.setEnabled(enabled)
    
    def get_copies_count(self):
        """Get the number of copies to make."""
        return self.copies_spinbox.value()
    
    def get_lock_state(self):
        """Get the lock checkbox state."""
        return self.copy_lock_checkbox.isChecked()