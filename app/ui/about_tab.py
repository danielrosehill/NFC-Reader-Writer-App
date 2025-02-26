"""
About Tab UI components for the NFC Reader/Writer application.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QColor

class AboutTab(QWidget):
    """About Tab UI component."""
    
    def __init__(self, parent=None):
        """Initialize the About Tab UI."""
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the about tab interface."""
        layout = QVBoxLayout(self)
        
        # Header section with app info
        header_group = QGroupBox("About NFC Reader/Writer")
        header_layout = QVBoxLayout(header_group)
        
        # App icon
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # We'll set the icon in the controller
        self.icon_label = icon_label
        header_layout.addWidget(icon_label)
        
        # Version info
        version_label = QLabel("Version 3.4")
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
            "and Claude Sonnet 3.7"
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
        
        # Changelog section
        changelog_group = QGroupBox("Changelog")
        changelog_layout = QVBoxLayout(changelog_group)
        
        changelog_text = QTextEdit()
        changelog_text.setReadOnly(True)
        changelog_text.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: none;
                padding: 15px;
            }
        """)
        changelog_text.setHtml("""
            <style>
                h4 { color: #1976d2; margin-top: 10px; margin-bottom: 5px; }
                ul { margin-left: 20px; line-height: 1.4; }
                li { margin-bottom: 6px; }
                .new { color: #2e7d32; }
                .fix { color: #d32f2f; }
                .improve { color: #1976d2; }
            </style>
            
            <h4>Version 3.4 (February 2025)</h4>
            <ul>
                <li><span class='improve'>IMPROVE:</span> Updated co-developer attribution</li>
                <li><span class='improve'>IMPROVE:</span> General performance enhancements</li>
                <li><span class='fix'>FIX:</span> Minor UI adjustments</li>
            </ul>
            
            <h4>Version 3.3 (February 2024)</h4>
            <ul>
                <li><span class='new'>NEW:</span> Dark mode toggle with Ctrl+T shortcut</li>
                <li><span class='new'>NEW:</span> Enhanced status bar with reader and tag status</li>
                <li><span class='new'>NEW:</span> Tab switching shortcuts (Ctrl+1/2/3)</li>
                <li><span class='improve'>IMPROVE:</span> Better keyboard shortcuts and tooltips</li>
                <li><span class='improve'>IMPROVE:</span> Enhanced URL validation and formatting</li>
                <li><span class='fix'>FIX:</span> Clipboard paste functionality</li>
            </ul>
            
            <h4>Version 3.2 (January 2024)</h4>
            <ul>
                <li><span class='new'>NEW:</span> Quick write button for single tags</li>
                <li><span class='new'>NEW:</span> Recent URLs dropdown</li>
                <li><span class='improve'>IMPROVE:</span> Enhanced tag detection reliability</li>
                <li><span class='improve'>IMPROVE:</span> Better visual feedback for write operations</li>
                <li><span class='fix'>FIX:</span> URL handling for local network addresses</li>
            </ul>
        """)
        changelog_layout.addWidget(changelog_text)
        
        layout.addWidget(changelog_group)
        layout.addWidget(manual_group)
    
    def set_icon(self, pixmap):
        """Set the app icon."""
        if pixmap and not pixmap.isNull():
            icon_pixmap = pixmap.scaled(QSize(64, 64), Qt.AspectRatioMode.KeepAspectRatio, 
                                       Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(icon_pixmap)
        else:
            # Create a default icon if image cannot be loaded
            default_pixmap = QPixmap(64, 64)
            default_pixmap.fill(QColor("#1976d2"))  # Use theme color
            self.icon_label.setPixmap(default_pixmap)