"""
Utility functions and constants for the NFC Reader/Writer application.
"""

import re
import subprocess
import time
import urllib.request
import urllib.error
import ssl
from typing import Optional, List, Tuple

# APDU Commands
GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
READ_PAGE = [0xFF, 0xB0, 0x00]  # Will append page number and length
LOCK_CARD = [0xFF, 0xD6, 0x00, 0x02, 0x04, 0x00, 0x00, 0x00, 0x00]

# URL prefixes according to NFC Forum URI Record Type Definition
URL_PREFIXES = {
    0x00: "http://www.",
    0x01: "https://www.",
    0x02: "http://",
    0x03: "https://",
    0x04: "tel:",
    0x05: "mailto:",
    0x06: "ftp://anonymous:anonymous@",
    0x07: "ftp://ftp.",
    0x08: "ftps://",
    0x09: "sftp://",
    0x0A: "smb://",
    0x0B: "nfs://",
    0x0C: "ftp://",
    0x0D: "dav://",
    0x0E: "news:",
    0x0F: "telnet://",
    0x10: "imap:",
    0x11: "rtsp://",
    0x12: "urn:",
    0x13: "pop:",
    0x14: "sip:",
    0x15: "sips:",
    0x16: "tftp:",
    0x17: "btspp://",
    0x18: "btl2cap://",
    0x19: "btgoep://",
    0x1A: "tcpobex://",
    0x1B: "irdaobex://",
    0x1C: "file://",
    0x1D: "urn:epc:id:",
    0x1E: "urn:epc:tag:",
    0x1F: "urn:epc:pat:",
    0x20: "urn:epc:raw:",
    0x21: "urn:epc:",
    0x22: "urn:nfc:",
}

def open_url_in_browser(url: str) -> bool:
    """
    Attempt to open a URL in a browser.
    
    Args:
        url: The URL to open
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not url.startswith(("http://", "https://")):
        return False
        
    try:
        # Try google-chrome first with timeout
        process = subprocess.Popen(['google-chrome', url], 
                                start_new_session=True)
        try:
            process.wait(timeout=3)
            return True
        except subprocess.TimeoutExpired:
            # Process started but didn't exit - this is normal
            return True
    except FileNotFoundError:
        try:
            # Fallback to chrome if google-chrome not found
            process = subprocess.Popen(['chrome', url], 
                                    start_new_session=True)
            try:
                process.wait(timeout=3)
                return True
            except subprocess.TimeoutExpired:
                return True
        except FileNotFoundError:
            # Last resort fallback to xdg-open
            try:
                process = subprocess.Popen(['xdg-open', url], 
                                        start_new_session=True)
                try:
                    process.wait(timeout=3)
                    return True
                except subprocess.TimeoutExpired:
                    return True
            except Exception:
                return False
    except Exception:
        return False

def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validate and normalize a URL.
    
    Args:
        url: The URL to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, normalized_url)
    """
    if not url:
        return False, url
        
    # Normalize URL format
    normalized_url = url.strip()
    
    # Add protocol if missing
    if normalized_url.startswith('www.'):
        normalized_url = 'https://' + normalized_url
    elif not normalized_url.startswith(('http://', 'https://')):
        # Check if it looks like a domain
        if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', normalized_url):
            normalized_url = 'https://' + normalized_url
    
    # Check if URL is a LAN IP and rewrite https:// to http://
    lan_ip_pattern = re.compile(r'^https://(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)')
    if lan_ip_pattern.match(normalized_url):
        normalized_url = 'http://' + normalized_url[8:]  # Replace https:// with http://
    
    # Basic URL validation
    is_valid = bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', normalized_url))
    
    return is_valid, normalized_url

def extract_url_from_data(data: List[int], toHexString) -> Optional[str]:
    """
    Extract URL from NDEF data if possible.
    
    Args:
        data: Raw tag data
        toHexString: Function to convert bytes to hex string
        
    Returns:
        Optional[str]: Extracted URL or None
    """
    try:
        # Basic check for NDEF message
        if len(data) < 8:  # Need minimum length for NDEF
            return None
            
        # Look for NDEF TLV
        for i in range(len(data) - 2):
            if data[i] == 0x03:  # NDEF TLV
                length = data[i+1]
                if i + 2 + length > len(data):
                    continue
                    
                # Check for URL record with improved detection for long URLs
                for j in range(i+2, i+2+length-4):
                    if data[j] == 0xD1 and data[j+3] == 0x55:  # URL record
                        url_prefix_byte = data[j+5]
                        prefix = URL_PREFIXES.get(url_prefix_byte, "")
                        
                        # Calculate the correct end position for the URL content
                        payload_length = data[j+2]
                        url_end = j + 6 + payload_length - 1  # -1 for the prefix byte
                        
                        # Ensure we don't exceed array bounds
                        if url_end > len(data):
                            url_end = len(data)
                            
                        url_content = bytes(data[j+6:url_end]).decode('utf-8', errors='replace')
                        return prefix + url_content.strip('\x00')  # Remove any null terminators
                        
                # Check for Text record
                for j in range(i+2, i+2+length-4):
                    if data[j] == 0xD1 and data[j+3] == 0x54:  # Text record
                        lang_code_length = data[j+5] & 0x3F
                        text_start = j+6+lang_code_length
                        text_end = j+2+data[j+2]
                        if text_start < text_end:
                            return bytes(data[text_start:text_end]).decode('utf-8', errors='replace').strip('\x00')
        return None
    except Exception:
        return None