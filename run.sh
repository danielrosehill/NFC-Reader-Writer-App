#!/bin/bash
#
# Run script for NFC Reader/Writer application
# This script runs the application directly from source
#

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}      NFC Reader/Writer Application Runner         ${NC}"
echo -e "${BLUE}====================================================${NC}"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
    exit 1
fi

# Change to the project directory if not already there
cd "$(dirname "$0")" || { echo -e "${RED}Failed to change to project directory${NC}"; exit 1; }

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
        
        # Verify installation
        if ! python3 -c "import $module" &> /dev/null; then
            echo -e "${RED}Failed to install $module. Please install manually:${NC}"
            echo -e "${YELLOW}pip3 install $module${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}All required modules installed successfully.${NC}"
else
    echo -e "${GREEN}All required modules are installed.${NC}"
fi

# Run the application
echo -e "${YELLOW}Starting NFC Reader/Writer application...${NC}"
echo ""

# Run the Python application
if python3 run.py; then
    echo ""
    echo -e "${GREEN}Application exited successfully.${NC}"
else
    echo ""
    echo -e "${RED}Application exited with an error.${NC}"
    echo -e "${YELLOW}Check the output above for details.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}Application session completed.${NC}"
echo -e "${BLUE}====================================================${NC}"

exit 0
