# NFC Reader/Writer Application

A user-friendly application for reading and writing NFC tags using the ACR1252U reader. Perfect for managing URL tags, text records, and batch operations.

## Features

- Read NFC tags and automatically detect URLs
- Write URLs to NFC tags with validation and formatting
- Copy tag content to multiple tags in batch mode
- Dark/light theme toggle
- Debug mode for troubleshooting
- Keyboard shortcuts for common operations

## Requirements

- Python 3.6+
- PyQt6
- pyscard
- ACR1252U NFC Reader or compatible device

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/NFC-Reader-Writer-App.git
   cd NFC-Reader-Writer-App
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application using:

```
python run.py
```

Or make it executable and run directly:

```
chmod +x run.py
./run.py
```

## Project Structure

The application has been refactored into a modular structure for better maintainability:

```
app/
├── __init__.py          # Package initialization
├── main.py              # Entry point
├── gui.py               # Main GUI class
├── reader.py            # NFC reader functionality
├── writer.py            # NFC writer functionality
├── copier.py            # NFC tag copying functionality
├── utils.py             # Utility functions
└── ui/                  # UI components
    ├── __init__.py
    ├── read_tab.py      # Read tab UI
    ├── write_tab.py     # Write tab UI
    ├── copy_tab.py      # Copy tab UI
    └── about_tab.py     # About tab UI
```

## Keyboard Shortcuts

- **Ctrl+1**: Switch to Read Tags tab
- **Ctrl+2**: Switch to Write Tags tab
- **Ctrl+3**: Switch to Copy Tags tab
- **Ctrl+4**: Switch to About tab
- **Ctrl+T**: Toggle dark/light theme
- **Ctrl+V**: Paste URL in write field
- **Ctrl+L**: Clear write field

## License

[MIT License](LICENSE)

## Acknowledgements

- Developed by Daniel Rosehill and Claude 3.5 Sonnet
- Icon from [ACR1252U documentation](https://www.acs.com.hk/en/products/342/acr1252u-usb-nfc-reader-iii-nfc-forum-certified-reader/)
