"""
NFC Writer functionality for the NFC Reader/Writer application.
"""

import time
from typing import List, Tuple, Callable, Any, Optional

from app.utils import GET_UID, LOCK_CARD, get_reader_specific_commands

class NFCWriter:
    """Class to handle NFC writer operations."""
    
    def __init__(self, toHexString_func, debug_callback=None):
        """
        Initialize the NFC writer.
        
        Args:
            toHexString_func: Function to convert bytes to hex string
            debug_callback: Callback for debug messages
        """
        self.toHexString = toHexString_func
        self.debug_callback = debug_callback
    
    def write_url_to_tag(self, connection, url: str, lock: bool = True) -> Tuple[bool, str]:
        """
        Write a URL to an NFC tag.
        Enhanced for better compatibility with different reader models.
        
        Args:
            connection: Active card connection
            url: URL to write
            lock: Whether to lock the tag after writing
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Verify tag presence with UID check
            # Get reader model to adjust writing strategy
            reader_str = str(connection.getReader())
            is_acr122u = "ACR122" in reader_str
            commands = get_reader_specific_commands(reader_str)
            
            response, sw1, sw2 = connection.transmit(commands['GET_UID'])
            if sw1 != 0x90:
                return False, f"Tag presence check failed: SW1={sw1:02X} SW2={sw2:02X}"
            
            uid = self.toHexString(response)
            
            # Create NDEF message for URL
            ndef_data = self._create_url_ndef(url)
            
            # ACR122U sometimes needs a small delay before initialization
            if is_acr122u:
                time.sleep(0.05)
            
            # Initialize NDEF capability
            init_command = [0xFF, 0xD6, 0x00, 0x03, 0x04, 0xE1, 0x10, 0x06, 0x0F]
            response, sw1, sw2 = connection.transmit(init_command)
            if sw1 != 0x90:
                return False, f"NDEF initialization failed: {sw1:02X} {sw2:02X}"
            
            # Write data in chunks of 4 bytes (one page at a time)
            # ACR122U sometimes needs a small delay after initialization
            if is_acr122u:
                time.sleep(0.05)
                
            chunk_size = 4
            for i in range(0, len(ndef_data), chunk_size):
                chunk = ndef_data[i:i + chunk_size]
                page = 4 + (i // chunk_size)  # Start from page 4
                
                # Pad the last chunk with zeros if needed
                if len(chunk) < chunk_size:
                    chunk = chunk + [0] * (chunk_size - len(chunk))
                
                write_command = [0xFF, 0xD6, 0x00, page, chunk_size] + chunk
                response, sw1, sw2 = connection.transmit(write_command)
                
                if sw1 != 0x90:
                    return False, f"Failed to write page {page}"
                
                # ACR122U may need a small delay between writes
                if is_acr122u:
                    time.sleep(0.02)
            
            # Lock the tag if requested
            if lock:
                # ACR122U sometimes needs a small delay before locking
                if is_acr122u:
                    time.sleep(0.1)
                    
                response, sw1, sw2 = connection.transmit(commands['LOCK_CARD'])
                if sw1 != 0x90:
                    return False, "Failed to lock tag"
                return True, f"URL written to tag {uid} and locked"
            
            return True, f"URL written to tag {uid}"
            
        except Exception as e:
            return False, f"Write error: {str(e)}"
    
    def _create_url_ndef(self, text: str) -> List[int]:
        """
        Create NDEF message for a URL.
        
        Args:
            text: URL text
            
        Returns:
            List[int]: NDEF message bytes
        """
        text_bytes = list(text.encode('utf-8'))
        
        # URL prefixes according to NFC Forum URI Record Type Definition
        url_prefixes = {
            'http://www.': 0x00,
            'https://www.': 0x01,
            'http://': 0x02,
            'https://': 0x03,
            'tel:': 0x04,
            'mailto:': 0x05,
        }
        
        # Determine record type and data
        prefix_found = None
        remaining_text = text
        
        # Detect if the text looks like a web URL
        looks_like_web = any(
            "." + tld in text.lower() for tld in [
                "com", "org", "net", "edu", "gov", "io", "app"
            ]
        )
        
        # Determine record type and data
        if text.startswith(('http://www.', 'https://www.', 'http://', 'https://')):
            # This is a web URL with explicit prefix
            for prefix, code in url_prefixes.items():
                if text.startswith(prefix):
                    prefix_found = code
                    remaining_text = text[len(prefix):]
                    break
            if prefix_found is not None:
                # URL record with prefix
                remaining_bytes = list(remaining_text.encode('utf-8'))
                ndef_header = [0xD1, 0x01, len(remaining_bytes) + 1] + [0x55]  # Type: U (URL)
                record_data = [prefix_found] + remaining_bytes
            else:
                # Fallback to text if no prefix matched
                ndef_header = [0xD1, 0x01, len(text_bytes) + 1] + [0x54] + [0x00]  # Type: T (Text)
                record_data = text_bytes
        elif looks_like_web:
            # This looks like a web URL without explicit prefix, add http://
            prefix_found = 0x02  # http://
            remaining_bytes = list(text.encode('utf-8'))
            ndef_header = [0xD1, 0x01, len(remaining_bytes) + 1] + [0x55]  # Type: U (URL)
            record_data = [prefix_found] + remaining_bytes
        else:
            # Store as plain text (including tel: and mailto: URLs)
            ndef_header = [0xD1, 0x01, len(text_bytes) + 1] + [0x54] + [0x00]  # Type: T (Text)
            record_data = text_bytes
        
        # Calculate total length including headers
        total_length = len(ndef_header) + len(record_data)
        
        # TLV format: 0x03 (NDEF) + length + NDEF message + 0xFE (terminator)
        ndef_data = [0x03, total_length] + ndef_header + record_data + [0xFE]
        
        return ndef_data
    
    def batch_write_tags(self, reader, url: str, quantity: int, lock: bool = True, 
                         progress_callback: Optional[Callable[[int, int], None]] = None,
                         status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Write the same URL to multiple tags.
        
        Args:
            reader: NFCReader instance
            url: URL to write
            quantity: Number of tags to write
            lock: Whether to lock tags after writing
            progress_callback: Callback for progress updates
            status_callback: Callback for status updates
            
        Returns:
            bool: True if all tags were written successfully
        """
        tags_written = 0
        last_uid = None
        
        if status_callback:
            status_callback(f"Ready to write URL: {url}")
        
        try:
            while tags_written < quantity:
                try:
                    connection, connected = reader.connect_with_retry()
                    if not connected:
                        time.sleep(0.2)
                        continue
                        
                    # Get UID to check if it's a new tag
                    reader_str = str(connection.getReader())
                    commands = get_reader_specific_commands(reader_str)
                    response, sw1, sw2 = connection.transmit(commands['GET_UID'])
                    if sw1 == 0x90:
                        uid = self.toHexString(response)
                        if uid != last_uid:  # Only write to new tags
                            last_uid = uid
                            
                            if status_callback:
                                status_callback(f"Writing to tag {uid}...")
                            
                            # Write the URL
                            success, message = self.write_url_to_tag(connection, url, lock)
                            
                            if success:
                                tags_written += 1
                                
                                if progress_callback:
                                    progress_callback(tags_written, quantity)
                                
                                if tags_written == quantity:
                                    if status_callback:
                                        status_callback(f"Successfully wrote {quantity} tags")
                                    return True
                                else:
                                    if status_callback:
                                        status_callback(f"Wrote tag {tags_written}/{quantity}. Please present next tag.")
                            else:
                                if status_callback:
                                    status_callback(f"Error: {message}")
                    
                    connection.disconnect()
                    
                except Exception as e:
                    error_msg = str(e)
                    if not any(msg in error_msg.lower() for msg in [
                        "card is not connected",
                        "no smart card inserted",
                        "card is unpowered"
                    ]) and status_callback:
                        status_callback(f"Error: {error_msg}")
                    
                    # Small delay to prevent CPU overload
                    time.sleep(0.1)
        except Exception as e:
            # Catch any exceptions that might occur in the main loop
            if status_callback:
                status_callback(f"Critical error: {str(e)}")
            if self.debug_callback:
                self.debug_callback("Error", f"Critical error in batch_write_tags: {str(e)}")
            return False
            
        return tags_written > 0