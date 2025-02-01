#!/usr/bin/env python3

from typing import List, Optional, Tuple
import time

class NFCReader:
    # APDU Commands
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    SELECT_NDEF = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
    READ_BINARY = [0x00, 0xB0, 0x00, 0x00, 0x0F]
    
    def __init__(self):
        """Initialize the NFC reader."""
        try:
            from smartcard.System import readers
            from smartcard.Exceptions import NoReadersException
            from smartcard.util import toHexString
            self.readers = readers
            self.toHexString = toHexString
        except ImportError:
            print("Warning: pyscard not installed. Please install required packages:")
            print("sudo zypper install pcsc-lite-devel")
            print("pip install pyscard")
            return

    def list_readers(self):
        """List all available NFC readers."""
        try:
            available_readers = self.readers()
            if not available_readers:
                print("No NFC readers found.")
                return []
            
            print("Found readers:", available_readers)
            return available_readers
        except Exception as e:
            print(f"Error listing readers: {str(e)}")
            return []

    def connect_reader(self, reader):
        """Connect to a specific reader."""
        try:
            connection = reader.createConnection()
            connection.connect()
            return connection
        except Exception as e:
            print(f"Error connecting to reader: {str(e)}")
            return None

    def read_tag(self, connection) -> Optional[str]:
        """Read data from an NFC tag."""
        try:
            # Get UID
            response, sw1, sw2 = connection.transmit(self.GET_UID)
            if sw1 != 0x90:
                print(f"Error getting UID. Status: {sw1:02X} {sw2:02X}")
                return None
            
            uid = self.toHexString(response)
            print(f"Tag UID: {uid}")
            
            # Try to read NDEF content
            try:
                # Select NDEF application
                response, sw1, sw2 = connection.transmit(self.SELECT_NDEF)
                if sw1 == 0x90:
                    # Read NDEF data
                    response, sw1, sw2 = connection.transmit(self.READ_BINARY)
                    if sw1 == 0x90:
                        ndef_data = self.toHexString(response)
                        print(f"NDEF Content: {ndef_data}")
                        self._parse_ndef(response)
            except Exception as e:
                print(f"Note: NDEF read failed (this is normal for non-NDEF tags): {str(e)}")
            
            return uid
            
        except Exception as e:
            print(f"Error reading tag: {str(e)}")
            return None

    def write_tag(self, connection, data: List[int]) -> bool:
        """Write data to an NFC tag."""
        try:
            # First, try to write as NDEF
            success = self._write_ndef(connection, data)
            if success:
                return True
                
            # If NDEF fails, try direct write (for MIFARE Classic)
            print("NDEF write failed, trying direct write...")
            write_command = [0xFF, 0xD6, 0x00, 0x00, len(data)] + data
            response, sw1, sw2 = connection.transmit(write_command)
            
            if sw1 == 0x90:
                print("Data written successfully")
                return True
            else:
                print(f"Error writing data. Status: {sw1:02X} {sw2:02X}")
                return False
        except Exception as e:
            print(f"Error writing to tag: {str(e)}")
            return False
            
    def _write_ndef(self, connection, data: List[int]) -> bool:
        """Try to write data as NDEF message."""
        try:
            # Select NDEF application
            response, sw1, sw2 = connection.transmit(self.SELECT_NDEF)
            if sw1 != 0x90:
                return False
                
            # Create NDEF message
            ndef_header = [0xD1, 0x01, len(data)] + [0x54] + [len(data)]  # TNF=1 (Text), SR=1, MB=1, ME=1
            ndef_data = ndef_header + data
            
            # Write NDEF message
            write_command = [0x00, 0xD6, 0x00, 0x00, len(ndef_data)] + ndef_data
            response, sw1, sw2 = connection.transmit(write_command)
            
            return sw1 == 0x90
        except:
            return False
            
    def _parse_ndef(self, data: List[int]) -> None:
        """Parse and display NDEF message content."""
        try:
            if len(data) < 2:
                return
                
            # Check for NDEF message header
            if data[0] == 0x00:  # NDEF message present
                length = data[1]
                if length > 0:
                    # Try to decode as text
                    try:
                        text = bytes(data[2:2+length]).decode('utf-8')
                        print(f"Decoded NDEF Text: {text}")
                    except:
                        print("NDEF content is not text format")
        except Exception as e:
            print(f"Error parsing NDEF: {str(e)}")

def main():
    """Main function to demonstrate usage."""
    reader = NFCReader()
    
    # List available readers
    available_readers = reader.list_readers()
    if not available_readers:
        return

    # Find ACR1252U reader
    acr1252_reader = None
    for r in available_readers:
        if "ACR1252" in str(r):
            acr1252_reader = r
            break
    
    if not acr1252_reader:
        print("ACR1252U reader not found. Please make sure it's connected.")
        return

    print(f"\nUsing reader: {acr1252_reader}")
    
    # Connect to the ACR1252U reader
    connection = reader.connect_reader(acr1252_reader)
    if not connection:
        return
    
    print("\nReady to read/write NFC tags.")
    print("Commands:")
    print("  r - Read tag (UID and NDEF content if available)")
    print("  w - Write data to tag (will try NDEF first, then direct write)")
    print("  t - Write text as NDEF message")
    print("  q - Quit")
    
    while True:
        cmd = input("\nEnter command (r/w/t/q): ").lower()
        
        if cmd == 'q':
            break
        elif cmd == 'r':
            print("\nWaiting for tag to read...")
            uid = reader.read_tag(connection)
        elif cmd == 'w':
            try:
                data = input("Enter data to write (hex format, e.g., 00 01 02 03): ")
                hex_data = [int(x, 16) for x in data.split()]
                print("\nWaiting for tag to write...")
                reader.write_tag(connection, hex_data)
            except ValueError:
                print("Invalid hex data format. Please use space-separated hex values (e.g., 00 01 02 03)")
        elif cmd == 't':
            try:
                text = input("Enter text to write: ")
                # Convert text to bytes and create NDEF message
                text_bytes = list(text.encode('utf-8'))
                print("\nWaiting for tag to write...")
                reader.write_tag(connection, text_bytes)
            except Exception as e:
                print(f"Error writing text: {str(e)}")
        else:
            print("Invalid command")

if __name__ == "__main__":
    main()
