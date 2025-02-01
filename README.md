# NFC Reader/Writer for ACR1252U

![alt text](screenshots/v3/2.png)

![Made With Claude Sonnet 3.5](https://img.shields.io/badge/Made_With-Claude_Sonnet_3.5-blue)  
![Made With Cline IDE](https://img.shields.io/badge/Made_With-Cline_IDE-green)

This is a Python implementation for reading and writing NFC tags using the ACR1252U NFC reader. The application features a modern dark-themed PyQt6 graphical interface with comprehensive NFC tag reading and writing capabilities.

## Key Features

- Modern dark-themed PyQt6 interface
- Real-time URL detection with clipboard support
- Comprehensive NDEF message interpretation
- Batch writing capability
- Tag locking functionality
- Detailed debug logging
- Chrome browser integration

## Screenshots - V5

### Writing Mode

The GUI supports the ability to write URLs to NFC tags and write and lock in one operation. 

![alt text](screenshots/v5/1.png)

![alt text](screenshots/v3/2.png)

## Reading Mode

Reading mode supports continuous reading operation, detected URL display, and automatic opening of URLs in Google Chrome.

![alt text](screenshots/v5/3.png)

## Generated With Claude Sonnet 3.5 + Cline IDE!

![alt text](screenshots/1.png)

## My Testing Environment

- OpenSUSE Tumbleweed + KDE Plasma

## My Notes

---

# Claude Generated Readme

## Prerequisites

- Python 3.x
- OpenSUSE packages:
  ```bash
  sudo zypper install pcsc-lite-devel
  ```
- Python packages:
  ```bash
  pip install pyscard PyQt6
  ```

## Usage

### Command Line Interface
```bash
python nfc_reader.py
```

### Graphical User Interface
```bash
python nfc_gui.py
```

The GUI version provides:
1. Continuous tag scanning with automatic URL detection
2. Separate read and write interfaces
3. Automatic opening of URLs in Google Chrome
4. Tag locking functionality

## Features

### Command Line Interface
- Automatic detection of ACR1252U reader
- Read NFC tag UIDs
- NDEF message support
- Fallback to direct write for non-NDEF tags
- Interactive command menu

### GUI Interface
- Real-time tag scanning with debug information
- Automatic URL detection and Chrome browser integration
- Two-tab interface:
  1. Read Tab:
     - Continuous tag scanning
     - Real-time status updates
     - URL detection display with copy functionality
     - Detailed debug output showing:
       * Raw tag data
       * NDEF structure parsing
       * Content interpretation
       * URL detection steps
     - Automatic URL opening in Chrome
     - Comprehensive log display with copy/clear functions
  2. Write Tab:
     - Smart URL/Text detection
     - Proper NDEF formatting for both URLs and text
     - Batch writing support
     - Optional tag locking after writing
     - Debug output of written data
     - Progress tracking for batch operations
     - Status feedback
- Thread-safe operation
- Dark theme for improved visibility

### NTAG213 Support
- Optimized for NTAG213 memory structure
- Correct page addressing (starts at page 4)
- Proper NDEF formatting
- Compatible locking mechanism

## Supported Operations

### Reading Operations
- Universal tag UID reading
- NDEF message content reading with detailed parsing
- Automatic text content decoding
- URL detection with Chrome browser integration
- Continuous scanning mode with debug output
- Raw data inspection capabilities

### Writing Operations
- Smart URL/Text type detection
- Proper NDEF message formatting:
  * URL records (Type U)
  * Text records (Type T)
- NTAG213 memory layout compliance
- Tag locking support
- Batch writing capability
- Progress tracking
- Debug output of written data

## Interface Commands

### Command Line Interface
- `r` - Read tag (displays UID and NDEF content)
- `w` - Write raw data to tag (hex format)
- `t` - Write text as NDEF message
- `q` - Quit the application

### GUI Interface
#### Read Tab
- Start/Stop Scanning button
- Real-time log display with copy/clear functions
- URL detection display with copy support
- Automatic URL handling
- Detailed debug logging

#### Write Tab
- Text/URL input field
- Batch quantity selector
- Lock tag checkbox
- Write button
- Progress tracking
- Status display with clear function

## Error Handling

Comprehensive error handling for:
- Missing dependencies
- No readers found
- Connection errors
- Read/write errors
- NDEF parsing errors
- Invalid input formats

## Notes

- NDEF operations are attempted first for maximum compatibility
- Fallback to direct write operations for non-NDEF tags
- Make sure the pcscd service is running:
  ```bash
  sudo systemctl start pcscd
  ```

## Troubleshooting

If you encounter issues:
1. Ensure pcscd service is running
2. Verify the reader is properly connected (check `lsusb`)
3. Make sure all dependencies are properly installed
4. Check if your NFC tag is supported and properly positioned
