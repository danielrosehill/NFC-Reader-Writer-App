#!/usr/bin/env python3

"""
Main entry point for the NFC Reader/Writer application v3.5.
"""
import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from app.gui import NFCReaderGUI

def exception_handler(exc_type, exc_value, exc_traceback):
    """
    Global exception handler to catch unhandled exceptions.
    This prevents the application from silently crashing.
    """
    # Log the error
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"Unhandled exception: {error_msg}", file=sys.stderr)
    
    # Show error dialog to user
    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Icon.Critical)
    error_dialog.setWindowTitle("Application Error")
    error_dialog.setText("An unexpected error occurred:")
    error_dialog.setInformativeText(str(exc_value))
    error_dialog.setDetailedText(error_msg)
    error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
    error_dialog.exec()

def main():
    """Main entry point for the NFC Reader/Writer application."""
    # Set up global exception handler
    sys.excepthook = exception_handler
    
    app = QApplication(sys.argv)
    window = NFCReaderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()