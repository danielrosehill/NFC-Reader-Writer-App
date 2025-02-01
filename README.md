# NFC Reader/Writer for ACR1252U

![Made With Claude Sonnet 3.5](https://img.shields.io/badge/Made_With-Claude_Sonnet_3.5-blue)  
![Made With Cline IDE](https://img.shields.io/badge/Made_With-Cline_IDE-green)

This is a Python implementation for reading and writing NFC tags using the ACR1252U NFC reader. It includes both a command-line interface and a graphical user interface.

## Generated With Claude Sonnet 3.5 + Cline IDE!

![alt text](screenshots/1.png)

## Prerequisites

- Python 3.x
- OpenSUSE packages:
  ```bash
  sudo zypper install pcsc-lite-devel
  sudo zypper install python312-tk  # For GUI support
  ```
- Python packages:
  ```bash
  pip install pyscard
  ```

Note: The GUI version requires tkinter, which is installed via python312-tk package on OpenSUSE.

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
     - Detailed debug output showing:
       * Raw tag data
       * NDEF structure parsing
       * Content interpretation
       * URL detection steps
     - Automatic URL opening in Chrome
     - Comprehensive log display
  2. Write Tab:
     - Smart URL/Text detection
     - Proper NDEF formatting for both URLs and text
     - Optional tag locking after writing
     - Debug output of written data
     - Status feedback
- Thread-safe operation

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
- Real-time log display
- Automatic URL handling

#### Write Tab
- Text/URL input field
- Lock tag checkbox
- Write button
- Status display

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
