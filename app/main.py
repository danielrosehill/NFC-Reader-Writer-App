#!/usr/bin/env python3

import sys
from PyQt6.QtWidgets import QApplication
from app.gui import NFCReaderGUI

def main():
    """Main entry point for the NFC Reader/Writer application."""
    app = QApplication(sys.argv)
    window = NFCReaderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()