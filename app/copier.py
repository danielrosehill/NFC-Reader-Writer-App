"""
NFC Tag Copying functionality for the NFC Reader/Writer application.
"""

import time
from typing import List, Tuple, Callable, Optional, Any

from app.utils import GET_UID, extract_url_from_data
from app.reader import NFCReader
from app.writer import NFCWriter

class NFCCopier:
    """Class to handle NFC tag copying operations with enhanced validation."""
    
    def __init__(self, reader: NFCReader, writer: NFCWriter, debug_callback=None):
        """
        Initialize the NFC copier.
        
        Args:
            reader: NFCReader instance
            writer: NFCWriter instance
            debug_callback: Callback for debug messages
        """
        self.reader = reader
        self.writer = writer
        self.debug_callback = debug_callback
        self.source_tag_data = None
        self.source_tag_url = None
        self.source_tag_uid = None
        self.copying = False
        self.copies_made = 0
        self.max_retries = 3  # Maximum number of retries for operations
    
    def read_source_tag(self, timeout: int = 30, 
                        status_callback: Optional[Callable[[str], None]] = None,
                        tag_info_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Read a source tag for copying with enhanced validation.
        
        Args:
            timeout: Timeout in seconds
            status_callback: Callback for status updates
            tag_info_callback: Callback for tag info updates
            
        Returns:
            bool: True if source tag was read successfully
        """
        self.source_tag_data = None
        self.source_tag_url = None
        self.source_tag_uid = None
        
        if status_callback:
            status_callback("Please present source tag to read...")
        
        if tag_info_callback:
            tag_info_callback("Waiting for source tag...")
        
        last_uid = None
        timeout_time = time.time() + timeout
        
        while time.time() < timeout_time:
            try:
                connection, connected = self.reader.connect_with_retry()
                if not connected:
                    time.sleep(0.2)
                    continue
                
                # Get UID with retry for reliability
                uid = None
                for retry in range(self.max_retries):
                    try:
                        response, sw1, sw2 = connection.transmit(GET_UID)
                        if sw1 == 0x90:
                            uid = self.reader.toHexString(response)
                            break
                    except Exception:
                        time.sleep(0.1)
                
                if not uid:
                    connection.disconnect()
                    time.sleep(0.2)
                    continue
                    
                if status_callback:
                    status_callback("Tag Detected - Reading...")
                
                # Only process if it's a new tag
                if uid != last_uid:
                    last_uid = uid
                    if self.debug_callback:
                        self.debug_callback("New tag detected", f"UID: {uid}")
                    
                    # Read tag memory with multiple attempts for reliability
                    memory_data = None
                    for retry in range(self.max_retries):
                        try:
                            # Use the extended read function to ensure we capture long URLs
                            data = self.reader.read_tag_memory_full(connection)
                            if data and len(data) > 8:  # Ensure we have enough data
                                memory_data = data
                                break
                        except Exception as e:
                            if self.debug_callback:
                                self.debug_callback("Error", f"Read attempt {retry+1} failed: {str(e)}")
                            time.sleep(0.2)
                    
                    if memory_data:
                        # Validate the data format
                        is_valid = self._validate_tag_data(memory_data)
                        
                        if is_valid:
                            self.source_tag_data = memory_data
                            self.source_tag_uid = uid
                            
                            if self.debug_callback:
                                self.debug_callback("Source tag", f"Read {len(memory_data)} bytes")
                            
                            # Extract URL or text from the tag data
                            url = extract_url_from_data(memory_data, self.reader.toHexString)
                            self.source_tag_url = url
                            
                            # Display the URL with better formatting for long URLs
                            if url:
                                if self.debug_callback:
                                    self.debug_callback("URL Detected", f"Found URL: {url}")
                                
                                if tag_info_callback:
                                    tag_info_callback(f"UID: {uid}\n\nURL Content:\n{url}")
                            else:
                                if self.debug_callback:
                                    self.debug_callback("Debug", "No URL found in tag data")
                                
                                if tag_info_callback:
                                    tag_info_callback(f"Source Tag UID: {uid}\nContent: Raw data ({len(memory_data)} bytes)")
                            
                            if status_callback:
                                status_callback("Source tag read successfully")
                            
                            connection.disconnect()
                            return True
                        else:
                            if self.debug_callback:
                                self.debug_callback("Error", "Invalid tag data format")
                            
                            if status_callback:
                                status_callback("Error: Invalid tag data format. Please try again.")
                    else:
                        if self.debug_callback:
                            self.debug_callback("Error", "Failed to read tag data after multiple attempts")
                        
                        if status_callback:
                            status_callback("Error: Failed to read tag. Please try again.")
                
                connection.disconnect()
            except Exception as e:
                error_msg = str(e)
                # Only log errors that aren't common disconnection messages
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]):
                    if self.debug_callback:
                        self.debug_callback("Error", f"Scan error: {error_msg}")
                
                last_uid = None  # Reset UID on error
                
            time.sleep(0.2)  # Delay between scans
        
        # Timeout
        if status_callback:
            status_callback("Timeout - No source tag detected")
        
        if tag_info_callback:
            tag_info_callback("No source tag scanned yet")
        
        return False
    
    def _validate_tag_data(self, data: List[int]) -> bool:
        """
        Validate tag data format.
        
        Args:
            data: Raw tag data
            
        Returns:
            bool: True if data format is valid
        """
        if not data or len(data) < 8:
            return False
        
        # Check for NDEF TLV structure
        ndef_found = False
        for i in range(len(data) - 2):
            if data[i] == 0x03:  # NDEF TLV
                length = data[i+1]
                if i + 2 + length <= len(data):
                    ndef_found = True
                    break
        
        return ndef_found
    
    def copy_to_new_tags(self, quantity: int, lock: bool = True,
                         status_callback: Optional[Callable[[str], None]] = None,
                         progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Copy source tag data to new tags with enhanced validation.
        
        Args:
            quantity: Number of copies to make
            lock: Whether to lock tags after writing
            status_callback: Callback for status updates
            progress_callback: Callback for progress updates
            
        Returns:
            bool: True if all copies were successful
        """
        if not self.source_tag_data:
            if self.debug_callback:
                self.debug_callback("Error", "No source tag data available")
            return False
        
        if not self.reader.reader:
            if self.debug_callback:
                self.debug_callback("Error", "Reader not connected")
            return False
        
        self.copying = True
        self.copies_made = 0
        
        # Extract URL from source tag data
        url = self.source_tag_url
        
        if url:
            if status_callback:
                status_callback(f"Ready to copy URL: {url}\nPlease present first target tag...")
            
            if self.debug_callback:
                self.debug_callback("Copy Operation", f"Copying URL: {url}")
        else:
            if status_callback:
                status_callback("Error: Could not extract URL from source tag")
            
            if self.debug_callback:
                self.debug_callback("Error", "Could not extract URL from source tag")
            
            self.copying = False
            return False
        
        # Copy to new tags
        tags_written = 0
        last_uid = None
        
        while tags_written < quantity and self.copying:
            try:
                connection, connected = self.reader.connect_with_retry()
                if not connected:
                    time.sleep(0.2)
                    continue
                
                # Get UID with retry for reliability
                uid = None
                for retry in range(self.max_retries):
                    try:
                        response, sw1, sw2 = connection.transmit(GET_UID)
                        if sw1 == 0x90:
                            uid = self.reader.toHexString(response)
                            break
                    except Exception:
                        time.sleep(0.1)
                
                if not uid:
                    connection.disconnect()
                    time.sleep(0.2)
                    continue
                
                # Skip if it's the same as the source tag
                if uid == self.source_tag_uid:
                    if status_callback:
                        status_callback("Source tag detected - Please use a different tag")
                    
                    connection.disconnect()
                    time.sleep(1)
                    continue
                
                # Only write to new tags
                if uid != last_uid:
                    last_uid = uid
                    
                    if status_callback:
                        status_callback(f"Writing to tag {uid}...")
                    
                    # Write the URL with retry for reliability
                    success = False
                    error_message = ""
                    
                    for retry in range(self.max_retries):
                        try:
                            result, message = self.writer.write_url_to_tag(connection, url, lock)
                            if result:
                                success = True
                                break
                            else:
                                error_message = message
                                time.sleep(0.2)
                        except Exception as e:
                            error_message = str(e)
                            time.sleep(0.2)
                    
                    if success:
                        # Verify the write was successful by reading back
                        verify_success = self._verify_tag_write(connection, url)
                        
                        if verify_success:
                            tags_written += 1
                            self.copies_made = tags_written
                            
                            if progress_callback:
                                progress_callback(tags_written, quantity)
                            
                            if status_callback:
                                if tags_written == quantity:
                                    status_callback(f"Successfully wrote {quantity} tags")
                                else:
                                    status_callback(f"Wrote tag {tags_written}/{quantity}. Please present next tag.")
                        else:
                            if status_callback:
                                status_callback("Verification failed - Tag write was incomplete")
                    else:
                        if status_callback:
                            status_callback(f"Error: {error_message}")
                
                connection.disconnect()
            except Exception as e:
                error_msg = str(e)
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]) and status_callback:
                    status_callback(f"Error: {error_msg}")
                
            time.sleep(0.2)
        
        self.copying = False
        return tags_written == quantity
    
    def _verify_tag_write(self, connection, expected_url: str) -> bool:
        """
        Verify that a tag was written correctly by reading it back.
        
        Args:
            connection: Active card connection
            expected_url: URL that should be on the tag
            
        Returns:
            bool: True if verification was successful
        """
        try:
            # Read the tag data
            memory_data = self.reader.read_tag_memory_full(connection)
            if not memory_data:
                return False
            
            # Extract URL from the tag data
            url = extract_url_from_data(memory_data, self.reader.toHexString)
            
            # Compare with expected URL
            if url and url == expected_url:
                return True
            
            # If URLs don't match exactly, check if they're functionally equivalent
            # (e.g., http://example.com vs https://example.com)
            if url and expected_url:
                # Strip protocol
                url_no_protocol = url.replace("http://", "").replace("https://", "")
                expected_no_protocol = expected_url.replace("http://", "").replace("https://", "")
                
                # Strip trailing slashes
                url_no_protocol = url_no_protocol.rstrip("/")
                expected_no_protocol = expected_no_protocol.rstrip("/")
                
                if url_no_protocol == expected_no_protocol:
                    return True
            
            return False
        except Exception:
            return False
    
    def stop_copy_operation(self):
        """Stop the ongoing copy operation."""
        self.copying = False
    
    def reset(self):
        """Reset the copier state."""
        self.source_tag_data = None
        self.source_tag_url = None
        self.source_tag_uid = None
        self.copying = False
        self.copies_made = 0