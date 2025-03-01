"""
Utility functions and constants for the NFC Reader/Writer application.
"""

import re
import string
import subprocess
import time
import urllib.request
import urllib.error
import ssl
from typing import Optional, List, Tuple

# APDU Commands
# Standard PC/SC commands that work with most readers
GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
READ_PAGE = [0xFF, 0xB0, 0x00]  # Will append page number and length
LOCK_CARD = [0xFF, 0xD6, 0x00, 0x02, 0x04, 0x00, 0x00, 0x00, 0x00]

# Alternative commands for specific readers
# Some ACR122U readers might need these alternative commands
ALT_GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x04]  # With explicit length
ALT_READ_PAGE = [0xFF, 0xB0, 0x00]  # Same as READ_PAGE but might be used differently

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

def get_reader_specific_commands(reader_str: str) -> dict:
    """
    Get reader-specific commands based on the reader model.
    
    Args:
        reader_str: String representation of the reader
        
    Returns:
        dict: Dictionary of commands for the specific reader
    """
    commands = {
        'GET_UID': GET_UID,
        'READ_PAGE': READ_PAGE,
        'LOCK_CARD': LOCK_CARD
    }
    
    # ACR122U might need alternative commands in some cases
    if "ACR122" in reader_str:
        # For now, we're using the standard commands as they should work,
        # but we have alternatives available if needed
        # commands['GET_UID'] = ALT_GET_UID
        pass
        
    return commands

def open_url_in_browser(url: str) -> bool:
    """
    Attempt to open a URL in a browser.
    
    Args:
        url: The URL to open
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Add http:// prefix to URLs that don't have a protocol
    if not url.startswith(("http://", "https://")):
        # Check if it's an IP address or domain
        if re.match(r'^(\d{1,3}\.){3}\d{1,3}(:\d+)?', url) or '.' in url:
            url = "http://" + url
        else:
            return False  # Not a URL we can open
        
    try:
        # On Linux, use google-chrome as the primary browser
        try:
            subprocess.run(['google-chrome', '--new-window', url], 
                          check=False, 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL,
                          start_new_session=True,
                          timeout=1)  
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Fallback to xdg-open if google-chrome is not available
            try:
                subprocess.run(['xdg-open', url], 
                              check=False, 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL,
                              start_new_session=True,
                              timeout=1)
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
    
    # Handle tel: prefix on web URLs
    if normalized_url.startswith('tel:') and ('.' in normalized_url or '/' in normalized_url.replace('tel:', '')):
        # This is likely a web URL incorrectly tagged with tel: prefix
        web_url = normalized_url.replace('tel:', '').strip()
        if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', web_url) or \
           re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', web_url):
            normalized_url = 'https://' + web_url
        else:
            normalized_url = 'http://' + web_url
    
    # Fix common URL typos
    if normalized_url.startswith(('ttps://', 'tps://', 'tp://')):
        normalized_url = 'h' + normalized_url
    elif normalized_url.startswith(('ttp://', 'tp://')):
        normalized_url = 'h' + normalized_url
    elif normalized_url.startswith('htttps://'):
        normalized_url = 'https://' + normalized_url[8:]
    
    # Add protocol if missing
    if normalized_url.startswith('www.'):
        normalized_url = 'https://' + normalized_url
    elif not normalized_url.startswith(('http://', 'https://')):
        # Check if it looks like a domain
        if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', normalized_url) or \
           re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', normalized_url):
            normalized_url = 'https://' + normalized_url
    
    # Check if URL is a LAN IP and rewrite https:// to http://
    lan_ip_pattern = re.compile(r'^https://(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)')
    if lan_ip_pattern.match(normalized_url):
        normalized_url = 'http://' + normalized_url[8:]  # Replace https:// with http://
    
    # More lenient URL validation
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
                    # Check for URL record (D1 with type U)
                    if j+3 < len(data) and data[j] == 0xD1 and data[j+3] == 0x55:  # URL record
                        # Get URL prefix from the first byte of payload
                        url_prefix_byte = data[j+4]
                        prefix = URL_PREFIXES.get(url_prefix_byte, "")
                        
                        # Calculate the correct end position for the URL content
                        payload_length = data[j+2]
                        url_start = j + 5  # Skip record header and prefix byte
                        url_end = j + 5 + payload_length - 1  # -1 for the prefix byte
                        
                        # Ensure we don't exceed array bounds
                        if url_end > len(data):
                            url_end = len(data)
                            
                        url_content = bytes(data[url_start:url_end]).decode('utf-8', errors='replace')
                        
                        # Fix for URLs starting with 10.0.0.1
                        if url_content.startswith("0.0.0.1"):
                            url_content = "10.0.0.1" + url_content[7:]
                        
                        # Clean up the URL by removing any non-printable or special characters
                        cleaned_url = ""
                        for char in url_content:
                            if char in string.printable and char != '':
                                cleaned_url += char
                        
                        # Get the complete URL
                        complete_url = prefix + cleaned_url.strip()
                        
                        # Check if this is a tel: prefix but actually looks like a web URL
                        if complete_url.startswith('tel:') and ('.' in cleaned_url or '/' in cleaned_url):
                            # This is likely a web URL incorrectly tagged with tel: prefix
                            # Strip the tel: prefix and check if it looks like a domain
                            web_url = cleaned_url.strip()
                            if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', web_url) or \
                               re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', web_url):
                                complete_url = 'https://' + web_url
                            else:
                                complete_url = 'http://' + web_url
                        
                        # Fix common URL typos
                        if complete_url.startswith(('ttps://', 'tps://', 'tp://')):
                            complete_url = 'h' + complete_url
                        elif complete_url.startswith(('ttp://', 'tp://')):
                            complete_url = 'h' + complete_url
                        elif complete_url.startswith('htttps://'):
                            complete_url = 'https://' + complete_url[8:]
                        
                        # Add protocol if missing and looks like a domain
                        if not complete_url.startswith(('http://', 'https://')):
                            if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', complete_url) or \
                               re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', complete_url):
                                complete_url = 'https://' + complete_url
                        
                        return complete_url
                # Check for Text record
                for j in range(i+2, i+2+length-4):
                    if data[j] == 0xD1 and data[j+3] == 0x54:  # Text record
                        lang_code_length = data[j+5] & 0x3F
                        text_start = j+6+lang_code_length
                        text_end = j+2+data[j+2]
                        if text_start < text_end:
                            text_content = bytes(data[text_start:text_end]).decode('utf-8', errors='replace').strip('\x00')
                            
                            # Fix for URLs starting with 10.0.0.1
                            if text_content.startswith("0.0.0.1"):
                                text_content = "10.0.0.1" + text_content[7:]
                            
                            # Clean up the text by removing any non-printable or special characters
                            cleaned_text = ""
                            for char in text_content:
                                if char in string.printable and char != '':
                                    cleaned_text += char
                            
                            cleaned_text = cleaned_text.strip()
                            
                            # Check if the text looks like a URL
                            if re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', cleaned_text) or \
                               re.match(r'^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', cleaned_text):
                                return 'https://' + cleaned_text
                                
                            # Fix common URL typos
                            if cleaned_text.startswith(('ttps://', 'tps://', 'tp://')):
                                return 'h' + cleaned_text
                            elif cleaned_text.startswith(('ttp://', 'tp://')):
                                return 'h' + cleaned_text
                            elif cleaned_text.startswith('htttps://'):
                                return 'https://' + cleaned_text[8:]
                            
                            return cleaned_text
        return None
    except Exception:
        return None