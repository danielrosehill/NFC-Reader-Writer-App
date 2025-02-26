"""
NFC Reader functionality for the NFC Reader/Writer application.
"""

import time
from typing import List, Tuple, Optional, Any

from app.utils import GET_UID, READ_PAGE, get_reader_specific_commands

class NFCReader:
    """Class to handle NFC reader operations."""
    
    def __init__(self, readers_func, toHexString_func, debug_callback=None):
        """
        Initialize the NFC reader.
        
        Args:
            readers_func: Function to get available readers
            toHexString_func: Function to convert bytes to hex string
            debug_callback: Callback for debug messages
        """
        self.readers_func = readers_func
        self.toHexString = toHexString_func
        self.debug_callback = debug_callback
        self.reader = None
        self.tag_type = None
        self.last_connection_time = 0
    
    def find_reader(self):
        """
        Find and select an NFC reader.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            available_readers = self.readers_func()
            self.reader = None
            
            for r in available_readers:
                # Get reader details
                reader_str = str(r)
                reader_id = reader_str.split(" ")[0]
                
                # Known NFC reader models and their capabilities
                reader_models = {
                    "ACR1252": "ACR1252U",
                    "ACR122": "ACR122U", 
                    "ACS ACR122": "ACR122U",  # Alternative naming for ACR122U
                    "ACS ACR": "ACS Reader",  # More specific ACS match
                    "SCM Microsystems": "SCM Reader",
                    "OMNIKEY": "HID Omnikey",
                    "Sony": "Sony RC-S380",
                    "PN53": "PN532",
                    "USB Reader": "Generic USB Reader"  # For generic readers
                }
                
                # List of known non-NFC readers to ignore
                ignored_readers = [
                    "Yubico",
                    "YubiKey",
                    "Smart Card Reader",  # Generic smart card readers
                    "USB Smart Card Reader",
                    "Common Access Card",
                    "CAC Reader",
                    "PIV Reader",
                    "EMV Reader"
                ]
                
                # Check if this is a reader we should ignore
                if any(ignored in reader_str for ignored in ignored_readers):
                    continue
                
                # Find matching reader model
                reader_model = None
                for model_id, model_name in reader_models.items():
                    if model_id.lower() in reader_str.lower():  # Case-insensitive matching
                        reader_model = model_name
                        break
                
                # Only proceed if we found a known NFC reader model
                if reader_model is None:
                    # If no specific model is identified but it doesn't match ignored readers,
                    # try to use it as a generic reader
                    if not any(ignored.lower() in reader_str.lower() for ignored in ignored_readers):
                        reader_model = "Generic NFC Reader"
                    else:
                        continue
                
                self.reader = r
                return True, f"{reader_model} connected ({reader_id})"
            
            return False, "No NFC reader found"
        except Exception as e:
            return False, f"Error - {str(e)}"
    
    def connect_with_retry(self) -> Tuple[Any, bool]:
        """
        Try to connect to the card with retries.
        Enhanced to better support different reader models including ACR122U.
        
        Returns:
            Tuple[Any, bool]: (connection, success)
        """
        if not self.reader:
            return None, False

        # Get reader model to adjust connection strategy
        reader_str = str(self.reader)
        is_acr122u = "ACR122" in reader_str
            
        current_time = time.time()
        # ACR122U may need a slightly longer debounce time
        min_debounce = 0.15 if is_acr122u else 0.1
        if current_time - self.last_connection_time < min_debounce:
            return None, False
            
        self.last_connection_time = current_time
        
        try:
            connection = self.reader.createConnection()
        except Exception as e:
            if self.debug_callback:
                self.debug_callback("Error", f"Failed to create connection: {str(e)}")
            return None, False
        
        # Try different protocols with retries
        # ACR122U sometimes needs more retries
        max_attempts = 6 if is_acr122u else 5
        
        # Prioritize protocols based on reader model
        # ACR122U tends to work better with T0 protocol first
        protocols = ['T0', 'T1', 'T=0', 'T=1', None] if is_acr122u else ['T1', 'T0', 'T=1', 'T=0', None]
        
        for attempt in range(max_attempts):
            for protocol in protocols:
                try:
                    if protocol:
                        if protocol.startswith('T='):
                            connection.connect(protocol=protocol)
                        else:
                            connection.connect(cardProtocol=protocol)
                    else:
                        connection.connect()
                        
                    # Verify connection with GET_UID command
                    try:
                        response, sw1, sw2 = connection.transmit(GET_UID)
                        if sw1 == 0x90:
                            if self.debug_callback:
                                self.debug_callback("Debug", f"Connected with protocol: {protocol}")
                            return connection, True
                    except:
                        # If UID check fails, connection might not be stable
                        continue
                        
                except Exception as e:
                    if attempt == 4 and self.debug_callback:  # Only log on last attempt
                        self.debug_callback("Debug", f"Connection attempt failed with {protocol}: {str(e)}")
                    # ACR122U may need slightly longer delays between attempts
                    time.sleep((0.15 if is_acr122u else 0.1) * (attempt + 1))
                    
                try:
                    connection.disconnect()
                except:
                    pass
                    
        if self.debug_callback:
            self.debug_callback("Debug", "All connection attempts failed")
        return None, False
    
    def detect_tag_type(self, connection) -> str:
        """
        Detect the NFC tag type based on memory size and capabilities.
        
        Args:
            connection: Active card connection
            
        Returns:
            str: Detected tag type (NTAG213, NTAG215, NTAG216, or Unknown)
        """
        try:
            reader_str = str(self.reader)
            commands = get_reader_specific_commands(reader_str)
            
            # First get the UID to check if it's a valid tag
            response, sw1, sw2 = connection.transmit(commands['GET_UID'])
            if sw1 != 0x90:
                return "Unknown"
                
            # Try to read pages at different memory boundaries to determine tag type
            # NTAG213: 36 pages (144 bytes)
            # NTAG215: 126 pages (504 bytes)
            # NTAG216: 222 pages (888 bytes)
            
            # Try reading page 40 (just beyond NTAG213)
            try:
                read_cmd = commands['READ_PAGE'] + [40, 0x04]
                response, sw1, sw2 = connection.transmit(read_cmd)
                if sw1 != 0x90:
                    self.tag_type = "NTAG213"
                    return "NTAG213"
                    
                # If we can read page 40, it's at least NTAG215 or NTAG216
                self.tag_type = "NTAG215/216"
                return "NTAG215/216"
            except Exception as e:
                # If reading page 40 fails with an exception, assume it's NTAG213
                if self.debug_callback:
                    self.debug_callback("Debug", f"Error reading page 40: {str(e)}, assuming NTAG213")
                self.tag_type = "NTAG213"
                return "NTAG213"
        except Exception as e:
            if self.debug_callback:
                self.debug_callback("Error", f"Tag type detection failed: {str(e)}")
            self.tag_type = "Unknown"
            return "Unknown"
    
    def read_tag_memory(self, connection) -> List[int]:
        """
        Read NTAG213 memory pages.
        Enhanced for better compatibility with different reader models.
        
        Args:
            connection: Active card connection
            
        Returns:
            List[int]: Raw tag data
        """
        all_data = []
        
        # Get reader model to adjust reading strategy
        reader_str = str(self.reader)
        is_acr122u = "ACR122" in reader_str
        commands = get_reader_specific_commands(reader_str)
        
        # First verify tag presence with UID check
        try:
            response, sw1, sw2 = connection.transmit(commands['GET_UID'])
            if sw1 != 0x90:
                if self.debug_callback:
                    self.debug_callback("Error", f"Tag presence check failed: SW1={sw1:02X} SW2={sw2:02X}")
                return []
        except Exception as e:
            if self.debug_callback:
                self.debug_callback("Error", f"UID check failed: {str(e)}")
            return []
            
        # ACR122U sometimes needs a small delay after UID check
        if is_acr122u:
            time.sleep(0.05)
            
        # Read capability container (CC) first
        try:
            cc_cmd = commands['READ_PAGE'] + [3, 0x04]
            response, sw1, sw2 = connection.transmit(cc_cmd)
            if sw1 == 0x90:
                if self.debug_callback:
                    self.debug_callback("Debug", f"CC: {self.toHexString(response)}")
            else:
                if self.debug_callback:
                    self.debug_callback("Error", f"CC read failed: SW1={sw1:02X} SW2={sw2:02X}")
                return []
        except Exception as e:
            if self.debug_callback:
                self.debug_callback("Error", f"CC read error: {str(e)}")
            return []

        # ACR122U sometimes needs a small delay after CC read
        if is_acr122u:
            time.sleep(0.05)
            
        # NTAG213 has pages 4-39 available for user data
        for page in range(4, 40):
            try:
                read_cmd = commands['READ_PAGE'] + [page, 0x04]  # Read 4 bytes
                response, sw1, sw2 = connection.transmit(read_cmd)
                
                if sw1 == 0x90:
                    all_data.extend(response)
                    if self.debug_callback:
                        self.debug_callback("Debug", f"Page {page}: {self.toHexString(response)}")
                else:
                    if self.debug_callback:
                        self.debug_callback("Debug", f"Read stopped at page {page}: SW1={sw1:02X} SW2={sw2:02X}")
                    break
                    
                # Check for end of NDEF message
                if len(response) >= 4 and response[0] == 0xFE:
                    if self.debug_callback:
                        self.debug_callback("Debug", "Found NDEF terminator, stopping read")
                    break
                    
                # ACR122U may need a small delay between page reads
                if is_acr122u:
                    time.sleep(0.02)
                    
            except Exception as e:
                if self.debug_callback:
                    self.debug_callback("Error", f"Error reading page {page}: {str(e)}")
                break
                
        if not all_data and self.debug_callback:
            self.debug_callback("Error", "No data read from tag")
            
        return all_data
    
    def read_tag_memory_full(self, connection) -> List[int]:
        """
        Read NTAG213/215/216 memory pages with extended capacity for longer URLs.
        Enhanced for better compatibility with different reader models.
        
        Args:
            connection: Active card connection
            
        Returns:
            List[int]: Raw tag data
        """
        all_data = []
        
        # Get reader model to adjust reading strategy
        reader_str = str(self.reader)
        is_acr122u = "ACR122" in reader_str
        commands = get_reader_specific_commands(reader_str)
        
        # First verify tag presence with UID check
        try:
            response, sw1, sw2 = connection.transmit(commands['GET_UID'])
            if sw1 != 0x90:
                if self.debug_callback:
                    self.debug_callback("Error", f"Tag presence check failed: SW1={sw1:02X} SW2={sw2:02X}")
                return []
        except Exception as e:
            if self.debug_callback:
                self.debug_callback("Error", f"UID check failed: {str(e)}")
            return []
            
        # ACR122U sometimes needs a small delay after UID check
        if is_acr122u:
            time.sleep(0.05)
            
        # Read capability container (CC) first
        try:
            cc_cmd = commands['READ_PAGE'] + [3, 0x04]
            response, sw1, sw2 = connection.transmit(cc_cmd)
            if sw1 == 0x90:
                if self.debug_callback:
                    self.debug_callback("Debug", f"CC: {self.toHexString(response)}")
            else:
                if self.debug_callback:
                    self.debug_callback("Error", f"CC read failed: SW1={sw1:02X} SW2={sw2:02X}")
                return []
        except Exception as e:
            if self.debug_callback:
                self.debug_callback("Error", f"CC read error: {str(e)}")
            return []
            
        # ACR122U sometimes needs a small delay after CC read
        if is_acr122u:
            time.sleep(0.05)
            
        # Read extended range of pages to ensure we capture long URLs
        # NTAG213: pages 4-39
        # NTAG215: pages 4-129
        # NTAG216: pages 4-225
        # We'll try to read up to page 129 (NTAG215) to support longer URLs,
        # but use a smaller range for ACR122U to avoid timeouts
        max_page = 80 if is_acr122u else 130
        for page in range(4, max_page):
            try:
                read_cmd = commands['READ_PAGE'] + [page, 0x04]  # Read 4 bytes
                response, sw1, sw2 = connection.transmit(read_cmd)
                
                if sw1 == 0x90:
                    all_data.extend(response)
                    if self.debug_callback:
                        self.debug_callback("Debug", f"Page {page}: {self.toHexString(response)}")
                else:
                    # If we get an error, we've likely reached the end of the tag's memory
                    if self.debug_callback:
                        self.debug_callback("Debug", f"Read stopped at page {page}: SW1={sw1:02X} SW2={sw2:02X}")
                    break
                    
                # Check for end of NDEF message
                if len(response) >= 4 and response[0] == 0xFE:
                    if self.debug_callback:
                        self.debug_callback("Debug", "Found NDEF terminator, stopping read")
                    break
                    
            except Exception as e:
                if self.debug_callback:
                    self.debug_callback("Error", f"Error reading page {page}: {str(e)}")
                break
                
        if not all_data and self.debug_callback:
            self.debug_callback("Error", "No data read from tag")
            
        return all_data
    
    def get_tag_uid(self, connection) -> Optional[str]:
        """
        Get the UID of the tag.
        
        Args:
            connection: Active card connection
            
        Returns:
            Optional[str]: UID as hex string or None
        """
        try:
            reader_str = str(connection.getReader())
            commands = get_reader_specific_commands(reader_str)
            response, sw1, sw2 = connection.transmit(commands['GET_UID'])
            if sw1 == 0x90:
                return self.toHexString(response)
            return None
        except Exception:
            return None