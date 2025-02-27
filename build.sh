#!/bin/bash
#
# Build script for NFC Reader/Writer application
# This script runs the Python build process and handles errors
#

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to the project directory if not already there
cd "$(dirname "$0")" || { echo -e "${RED}Failed to change to project directory${NC}"; exit 1; }

# Set repository directory
REPO_DIR="$(pwd)"

# Print header
echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}      NFC Reader/Writer Application Builder        ${NC}"
echo -e "${BLUE}====================================================${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
    exit 1
fi

# Check for PyInstaller
echo -e "${YELLOW}Checking for PyInstaller...${NC}"
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo -e "${YELLOW}PyInstaller not found. Attempting to install...${NC}"
    pip3 install PyInstaller
    
    # Verify installation
    if ! python3 -c "import PyInstaller" &> /dev/null; then
        echo -e "${RED}Failed to install PyInstaller. Please install manually:${NC}"
        echo -e "${YELLOW}pip3 install PyInstaller${NC}"
        exit 1
    fi
    echo -e "${GREEN}PyInstaller installed successfully.${NC}"
else
    echo -e "${GREEN}PyInstaller is already installed.${NC}"
fi

# Check for required modules
echo -e "${YELLOW}Checking for required Python modules...${NC}"
REQUIRED_MODULES=("PyQt6" "smartcard")
MISSING_MODULES=()

for module in "${REQUIRED_MODULES[@]}"; do
    if ! python3 -c "import $module" &> /dev/null; then
        MISSING_MODULES+=("$module")
    fi
done

if [ ${#MISSING_MODULES[@]} -ne 0 ]; then
    echo -e "${YELLOW}Some required modules are missing. Installing...${NC}"
    for module in "${MISSING_MODULES[@]}"; do
        echo -e "${YELLOW}Installing $module...${NC}"
        pip3 install "$module"
    done
else
    echo -e "${GREEN}All required modules are installed.${NC}"
fi

# Create a backup of the latest build
BACKUP_DIR="${REPO_DIR}/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/nfc-rw_backup_$TIMESTAMP.tar.gz"

echo -e "${YELLOW}Creating backup of source code...${NC}"
tar -czf "$BACKUP_FILE" --exclude="*.pyc" --exclude="__pycache__" --exclude="build" --exclude="dist" -C "$REPO_DIR" .
echo -e "${GREEN}Backup created at: $BACKUP_FILE${NC}"

# Run the build script
echo -e "${YELLOW}Starting build process...${NC}"
echo -e "${YELLOW}This may take a few minutes. Please be patient.${NC}"
echo ""

# Run the Python build script
if python3 build.py; then
    echo ""
    echo -e "${GREEN}Build completed successfully!${NC}"
    
    # Get the repository directory
    echo -e "${GREEN}The executable has been created in ${REPO_DIR}/dist${NC}"
    
    # Check if the executable exists and is executable
    EXECUTABLE="${REPO_DIR}/dist/nfc-rw"
    if [ -f "$EXECUTABLE" ] && [ -x "$EXECUTABLE" ]; then
        echo -e "${GREEN}Executable verified and ready to use.${NC}"
    else
        echo -e "${YELLOW}Warning: Executable may not have correct permissions.${NC}"
        echo -e "${YELLOW}Setting executable permissions...${NC}"
        chmod +x "$EXECUTABLE"
    fi
else
    echo ""
    echo -e "${RED}Build process failed.${NC}"
    echo -e "${YELLOW}Check the output above for errors.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}Build process completed.${NC}"
echo -e "${BLUE}====================================================${NC}"

# Ask if user wants to run the application
echo ""
read -p "Do you want to run the application now? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Launching NFC Reader/Writer application...${NC}"
    "${REPO_DIR}/dist/nfc-rw"
fi

exit 0
