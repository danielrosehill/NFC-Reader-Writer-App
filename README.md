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

- Python 3.11 (recommended for best compatibility)
- PyQt6
- pyscard
- ACR1252U NFC Reader or compatible device

### System Dependencies

Before installing the Python packages, you need to install these system dependencies:

**On Ubuntu/Debian:**
```bash
sudo apt-get install libpcsclite-dev swig
```

**On Fedora/RHEL/CentOS:**
```bash
sudo dnf install pcsc-lite-devel swig
```

**On macOS (using Homebrew):**
```bash
brew install pcsc-lite swig
```

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/NFC-Reader-Writer-App.git
   cd NFC-Reader-Writer-App
   ```

2. Create a virtual environment (recommended):
   
   **Using venv:**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Linux/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```
   
   **Using uv (faster alternative):**
   ```bash
   uv venv --python=3.11 .venv
   source .venv/bin/activate  # On Linux/macOS
   # or
   .venv\Scripts\activate     # On Windows
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   # or using uv (faster)
   uv pip install -r requirements.txt
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

## Building Packages

### Standalone Executable

To build a standalone executable:

```bash
python build.py
```

This will create an executable in the `dist` directory.

### AppImage (Linux)

To build an AppImage for Linux:

```bash
python build_appimage.py
```

This will create an AppImage in the `dist` directory that can be run on most Linux distributions without installation.

### Debian Package (Ubuntu)

To build a Debian package (.deb) for Ubuntu:

```bash
python build_deb.py
```

This will create a .deb package in the `dist` directory that can be installed with:

```bash
sudo dpkg -i dist/nfc-reader-writer_1.0.0_amd64.deb
```

The Debian package automatically:
- Installs required system dependencies (libpcsclite1, libpcsclite-dev, swig)
- Adds desktop integration (application menu entry and icon)
- Configures user permissions for NFC access

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
