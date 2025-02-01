#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import webbrowser
from typing import Optional, List, Tuple
import queue
import re
import subprocess

class NFCReaderGUI:
    # APDU Commands
    GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]
    # NTAG213 specific commands
    READ_PAGE = [0xFF, 0xB0, 0x00]  # Will append page number and length
    LOCK_CARD = [0xFF, 0xD6, 0x00, 0x02, 0x04, 0x00, 0x00, 0x00, 0x00]  # Lock pages 2-3

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NFC Reader/Writer")
        self.root.geometry("800x600")
        
        # Configure style
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Helvetica', 10))
        style.configure('TButton', font=('Helvetica', 10))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Status.TLabel', font=('Helvetica', 10, 'italic'))
        
        # Configure root window
        self.root.configure(bg='#f0f0f0')
        self.root.option_add('*TCombobox*Listbox.font', ('Helvetica', 10))
        
        # Initialize reader
        try:
            from smartcard.System import readers
            from smartcard.util import toHexString
            from smartcard.Exceptions import NoReadersException
            self.readers = readers
            self.toHexString = toHexString
        except ImportError:
            messagebox.showerror("Error", "pyscard not installed. Please install required packages.")
            self.root.destroy()
            return

        # Create main container with padding
        main_container = ttk.Frame(self.root, padding="20 10 20 10", style='TFrame')
        main_container.pack(expand=True, fill='both')
        
        # Create notebook for tabs with custom style
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # Create tabs
        self.read_frame = ttk.Frame(self.notebook)
        self.write_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.read_frame, text='Read Tags')
        self.notebook.add(self.write_frame, text='Write Tags')

        # Setup read interface
        self.setup_read_interface()
        
        # Setup write interface
        self.setup_write_interface()

        # Initialize variables
        self.scanning = False
        self.scan_thread = None
        self.tag_queue = queue.Queue()
        self.last_connection_time = 0
        
        # Start checking for reader
        self.check_reader()
        
        # Setup periodic queue check
        self.root.after(100, self.check_tag_queue)

    def setup_read_interface(self):
        # Status label with custom style
        status_frame = ttk.Frame(self.read_frame, style='TFrame')
        status_frame.pack(fill='x', padx=20, pady=10)
        self.status_label = ttk.Label(status_frame, text="Status: Waiting for reader...", 
                                    style='Status.TLabel')
        self.status_label.pack(side='left')

        # Scan button with improved style
        button_frame = ttk.Frame(self.read_frame, style='TFrame')
        button_frame.pack(fill='x', padx=20, pady=5)
        self.scan_button = ttk.Button(button_frame, text="Start Scanning", 
                                    command=self.toggle_scanning, width=20)
        self.scan_button.pack()

        # Log text with improved styling
        log_frame = ttk.LabelFrame(self.read_frame, text="Log", padding="10 5 10 10", style='TFrame')
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Make text selectable with improved font and colors
        self.log_text = tk.Text(log_frame, height=25, width=80, state='normal',
                               font=('Consolas', 10),
                               bg='#ffffff',
                               fg='#333333',
                               selectbackground='#0078d7',
                               selectforeground='#ffffff',
                               padx=5, pady=5)
        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Button frame with improved layout
        button_frame = ttk.Frame(self.read_frame, style='TFrame')
        button_frame.pack(fill='x', padx=20, pady=10)
        
        # Clear and Copy buttons side by side
        self.copy_button = ttk.Button(button_frame, text="Copy Log", command=self.copy_log)
        self.copy_button.pack(side='left', padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.pack(side='left', padx=5)

    def setup_write_interface(self):
        # Write interface with improved layout
        write_header = ttk.Label(self.write_frame, text="Enter URL or text to write:", 
                               style='Header.TLabel')
        write_header.pack(pady=(20,5), padx=20)
        
        # Content entry frame
        entry_frame = ttk.Frame(self.write_frame, style='TFrame')
        entry_frame.pack(fill='x', padx=20, pady=5)
        self.write_entry = ttk.Entry(entry_frame, width=50, font=('Helvetica', 10))
        self.write_entry.pack(fill='x', expand=True)
        
        # Batch writing frame
        batch_frame = ttk.Frame(self.write_frame, style='TFrame')
        batch_frame.pack(fill='x', padx=20, pady=5)
        
        ttk.Label(batch_frame, text="Number of tags to write:", 
                 style='TLabel').pack(side='left', padx=(0,5))
        
        self.quantity_var = tk.StringVar(value="1")
        self.quantity_spinbox = ttk.Spinbox(batch_frame, from_=1, to=100, 
                                          width=5, textvariable=self.quantity_var)
        self.quantity_spinbox.pack(side='left')

        # Options frame with improved layout
        options_frame = ttk.Frame(self.write_frame, style='TFrame')
        options_frame.pack(fill='x', padx=20, pady=10)
        
        # Lock checkbox with improved style
        self.lock_var = tk.BooleanVar(value=True)
        self.lock_checkbox = ttk.Checkbutton(options_frame, text="Lock tag after writing", 
                                           variable=self.lock_var)
        self.lock_checkbox.pack(side='left', padx=(0,10))

        # Write button with improved style
        self.write_button = ttk.Button(options_frame, text="Write to Tag", 
                                     command=self.write_tag, width=20)
        self.write_button.pack(side='left')

        # Progress frame
        self.progress_frame = ttk.LabelFrame(self.write_frame, text="Progress", 
                                           padding="10 5 10 10", style='TFrame')
        self.progress_frame.pack(fill='x', padx=20, pady=10)
        
        self.progress_var = tk.StringVar(value="")
        self.progress_label = ttk.Label(self.progress_frame, 
                                      textvariable=self.progress_var,
                                      style='Status.TLabel')
        self.progress_label.pack(fill='x', padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(self.write_frame, text="Status", 
                                    padding="10 5 10 10", style='TFrame')
        status_frame.pack(fill='x', padx=20, pady=10)
        
        # Status label and clear button with improved layout
        status_container = ttk.Frame(status_frame, style='TFrame')
        status_container.pack(fill='x', expand=True)
        
        self.write_status = ttk.Label(status_container, text="", style='Status.TLabel')
        self.write_status.pack(side='left', padx=5, fill='x', expand=True)
        
        self.clear_status = ttk.Button(status_container, text="Clear Status", 
            command=lambda: self.write_status.config(text=""), width=15)
        self.clear_status.pack(side='right', padx=5)

    def check_reader(self):
        """Check for ACR1252U reader and update status."""
        try:
            available_readers = self.readers()
            self.reader = None
            
            for r in available_readers:
                if "ACR1252" in str(r):
                    self.reader = r
                    self.status_label.config(text="Status: Reader connected")
                    return

            self.status_label.config(text="Status: ACR1252U not found")
        except Exception as e:
            self.status_label.config(text=f"Status: Error - {str(e)}")
        
        # Check again in 2 seconds
        self.root.after(2000, self.check_reader)

    def connect_with_retry(self) -> Tuple[any, bool]:
        """Try to connect to the card with retries."""
        current_time = time.time()
        if current_time - self.last_connection_time < 0.2:  # Minimum time between connection attempts
            return None, False
            
        self.last_connection_time = current_time
        connection = self.reader.createConnection()
        
        # Try different protocols with increasing delays
        for attempt in range(3):
            for protocol in ['T1', 'T0', None]:
                try:
                    if protocol:
                        connection.connect(cardProtocol=protocol)
                    else:
                        connection.connect()
                    return connection, True
                except:
                    time.sleep(0.1 * (attempt + 1))
        
        return None, False

    def read_tag_memory(self, connection) -> List[int]:
        """Read NTAG213 memory pages."""
        all_data = []
        # NTAG213 has pages 4-39 available for user data
        for page in range(4, 40):  # Read all available user pages
            try:
                read_cmd = self.READ_PAGE + [page, 0x04]  # Read 4 bytes
                response, sw1, sw2 = connection.transmit(read_cmd)
                if sw1 == 0x90:
                    all_data.extend(response)
                    self.tag_queue.put(("Debug", f"Page {page}: {self.toHexString(response)}"))
                else:
                    break  # Stop if we hit an error or end of memory
            except:
                break
        return all_data

    def toggle_scanning(self):
        """Toggle the scanning process."""
        if not self.scanning:
            self.scanning = True
            self.scan_button.config(text="Stop Scanning")
            self.tag_queue.put(("System", "Started scanning for tags"))
            self.scan_thread = threading.Thread(target=self.scan_loop, daemon=True)
            self.scan_thread.start()
        else:
            self.scanning = False
            self.scan_button.config(text="Start Scanning")
            self.tag_queue.put(("System", "Stopped scanning"))

    def scan_loop(self):
        """Continuous scanning loop."""
        last_uid = None
        
        while self.scanning:
            try:
                if self.reader:
                    connection, connected = self.connect_with_retry()
                    if not connected:
                        time.sleep(0.2)
                        continue
                        
                    # Get UID
                    response, sw1, sw2 = connection.transmit(self.GET_UID)
                    if sw1 == 0x90:
                        uid = self.toHexString(response)
                        
                        # Only process if it's a new tag
                        if uid != last_uid:
                            last_uid = uid
                            self.tag_queue.put(("New tag detected", f"UID: {uid}"))
                            
                            # Read tag memory
                            memory_data = self.read_tag_memory(connection)
                            if memory_data:
                                self.process_ndef_content(memory_data)
                    
                    connection.disconnect()
            except Exception as e:
                error_msg = str(e)
                # Only log errors that aren't common disconnection messages
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]):
                    self.tag_queue.put(("Error", f"Scan error: {error_msg}"))
                last_uid = None  # Reset UID on error
                
            time.sleep(0.2)  # Delay between scans

    def process_ndef_content(self, data: List[int]):
        """Process NDEF content and open URLs if found."""
        try:
            self.tag_queue.put(("Debug", f"Raw data: {self.toHexString(data)}"))
            
            if len(data) < 4:  # Need at least TLV header
                self.tag_queue.put(("Debug", f"Data too short for NDEF: {len(data)} bytes"))
                return
                
            # Check for NDEF message
            if data[0] == 0x03:  # NDEF TLV
                length = data[1]
                self.tag_queue.put(("Debug", f"NDEF TLV found, length: {length} bytes"))
                self.tag_queue.put(("Debug", f"Total data available: {len(data)} bytes"))
                
                if length > 0:
                    try:
                        # Parse NDEF record header
                        flags = data[2]  # Record header flags
                        tnf = flags & 0x07  # Type Name Format (last 3 bits)
                        is_first = (flags & 0x80) != 0  # MB (Message Begin)
                        is_last = (flags & 0x40) != 0   # ME (Message End)
                        cf_flag = (flags & 0x20) != 0   # CF (Chunk Flag)
                        sr_flag = (flags & 0x10) != 0   # SR (Short Record)
                        il_flag = (flags & 0x08) != 0   # IL (ID Length present)
                        
                        type_length = data[3]  # Length of the type field
                        payload_length = data[4]  # Length of the payload
                        record_type = data[5:5+type_length]  # Type field
                        
                        self.tag_queue.put(("Debug", f"Record flags: MB={is_first}, ME={is_last}, CF={cf_flag}, SR={sr_flag}, IL={il_flag}, TNF={tnf}"))
                        self.tag_queue.put(("Debug", f"Type length: {type_length}"))
                        self.tag_queue.put(("Debug", f"Payload length: {payload_length}"))
                        self.tag_queue.put(("Debug", f"Record type: {self.toHexString(record_type)}"))
                        self.tag_queue.put(("Debug", f"Record type as bytes: {bytes(record_type)}"))
                        
                        # Calculate payload offset based on flags
                        offset = 5 + type_length  # Skip header and type
                        if il_flag:
                            id_length = data[offset]
                            offset += 1 + id_length  # Skip ID length and ID field
                        
                        # Check record type (both as bytes and as ASCII)
                        record_type_bytes = bytes(record_type)
                        if record_type_bytes == b'U' or (len(record_type) == 1 and record_type[0] == 0x55):  # URL Record
                            url_prefix_byte = data[offset]  # First byte of payload is URL prefix
                            content_bytes = data[offset+1:offset+payload_length]  # Rest is URL
                            
                            # URL prefixes
                            url_prefixes = {
                                0x00: "http://www.",
                                0x01: "https://www.",
                                0x02: "http://",
                                0x03: "https://",
                                0x04: "tel:",
                                0x05: "mailto:",
                            }
                            
                            prefix = url_prefixes.get(url_prefix_byte, "")
                            url = prefix + bytes(content_bytes).decode('utf-8')
                            self.tag_queue.put(("Debug", f"URL prefix: {prefix}"))
                            self.tag_queue.put(("Debug", f"URL content: {bytes(content_bytes).decode('utf-8')}"))
                            self.tag_queue.put(("URL Detected", f"Complete URL: {url}"))
                            
                            try:
                                # Try to open URL with different methods
                                methods = [
                                    (['google-chrome', '--new-tab', url], "Chrome (new tab)"),
                                    (['google-chrome', url], "Chrome (existing window)"),
                                    (['xdg-open', url], "System default browser")
                                ]
                                
                                success = False
                                for cmd, method in methods:
                                    try:
                                        self.tag_queue.put(("Browser", f"Trying to open URL with {method}"))
                                        result = subprocess.run(cmd, capture_output=True, text=True)
                                        if result.returncode == 0:
                                            self.tag_queue.put(("Browser", f"Successfully opened URL with {method}"))
                                            success = True
                                            break
                                        else:
                                            self.tag_queue.put(("Debug", f"{method} failed: {result.stderr}"))
                                    except Exception as e:
                                        self.tag_queue.put(("Debug", f"{method} error: {str(e)}"))
                                        continue
                                
                                if not success:
                                    self.tag_queue.put(("Error", "Failed to open URL with any method"))
                            except Exception as e:
                                self.tag_queue.put(("Error", f"Failed to open URL: {str(e)}"))
                        elif record_type_bytes == b'T' or (len(record_type) == 1 and record_type[0] == 0x54):  # Text Record
                            # First byte contains text info
                            text_info = data[offset]
                            lang_code_length = text_info & 0x3F  # Lower 6 bits
                            content_start = offset + 1 + lang_code_length
                            content_bytes = data[content_start:content_start+payload_length-1-lang_code_length]
                            
                            # Show language code if present
                            if lang_code_length > 0:
                                lang_code = bytes(data[offset+1:offset+1+lang_code_length]).decode('utf-8')
                                self.tag_queue.put(("Debug", f"Language code: {lang_code}"))
                            
                            text = bytes(content_bytes).decode('utf-8')
                            self.tag_queue.put(("Text Record", f"Content: {text}"))
                        else:
                            self.tag_queue.put(("Debug", f"Unknown record type: {bytes(record_type)}"))
                    except Exception as e:
                        self.tag_queue.put(("Error", f"Failed to decode NDEF: {str(e)}"))
            else:
                self.tag_queue.put(("Debug", f"Not an NDEF TLV (expected 0x03, got 0x{data[0]:02X})"))
        except Exception as e:
            self.tag_queue.put(("Error", f"Error parsing NDEF: {str(e)}"))

    def check_tag_queue(self):
        """Check for new tag data and update the GUI."""
        try:
            while True:
                title, message = self.tag_queue.get_nowait()
                timestamp = time.strftime("%H:%M:%S", time.localtime())
                self.log_text.insert('end', f"\n[{timestamp}] [{title}] {message}")
                self.log_text.see('end')
        except queue.Empty:
            pass
        
        self.root.after(100, self.check_tag_queue)

    def copy_log(self):
        """Copy log content to clipboard."""
        content = self.log_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.tag_queue.put(("System", "Log content copied to clipboard"))

    def clear_log(self):
        """Clear the log text."""
        self.log_text.delete(1.0, tk.END)
        self.tag_queue.put(("System", "Log cleared"))

    def write_tag(self):
        """Write data to multiple tags."""
        if not self.reader:
            messagebox.showerror("Error", "Reader not connected")
            return

        text = self.write_entry.get().strip()
        if not text:
            messagebox.showerror("Error", "Please enter text to write")
            return
            
        try:
            quantity = int(self.quantity_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
            
        if quantity < 1:
            messagebox.showerror("Error", "Quantity must be at least 1")
            return
            
        self.write_status.config(text="Waiting for tags...")
        self.progress_var.set(f"Starting batch write: 0/{quantity} tags written")
        
        # Start batch writing in a separate thread
        threading.Thread(target=self.batch_write_tags, 
                       args=(text, quantity), 
                       daemon=True).start()

    def batch_write_tags(self, text: str, quantity: int):
        """Write the same data to multiple tags."""
        tags_written = 0
        last_uid = None
        
        while tags_written < quantity:
            try:
                connection, connected = self.connect_with_retry()
                if not connected:
                    time.sleep(0.2)
                    continue
                    
                # Get UID to check if it's a new tag
                response, sw1, sw2 = connection.transmit(self.GET_UID)
                if sw1 == 0x90:
                    uid = self.toHexString(response)
                    if uid != last_uid:  # Only write to new tags
                        last_uid = uid
                        self.write_status.config(
                            text=f"Writing to tag {uid}...")
                        
                        # Write the data

                        # Convert text to bytes
                        text_bytes = list(text.encode('utf-8'))
            
                        # Create NDEF message for NTAG213
                        # Check if it's a URL and determine prefix
                        url_prefixes = {
                            'http://www.': 0x00,
                            'https://www.': 0x01,
                            'http://': 0x02,
                            'https://': 0x03,
                            'tel:': 0x04,
                            'mailto:': 0x05,
                        }
                        
                        prefix_found = None
                        remaining_text = text
            
                        if any(text.startswith(prefix) for prefix in url_prefixes.keys()):
                            # This is a URL, find the matching prefix
                            for prefix, code in url_prefixes.items():
                                if text.startswith(prefix):
                                    prefix_found = code
                                    remaining_text = text[len(prefix):]
                                    break
                            
                            # URL record with prefix
                            remaining_bytes = list(remaining_text.encode('utf-8'))
                            ndef_header = [0xD1, 0x01, len(remaining_bytes) + 1] + [0x55]  # Type: U (URL)
                            record_data = [prefix_found] + remaining_bytes
                        else:
                            # Text record
                            ndef_header = [0xD1, 0x01, len(text_bytes) + 1] + [0x54] + [0x00]  # Type: T (Text)
                            record_data = text_bytes
                        
                        # Calculate total length including headers
                        total_length = len(ndef_header) + len(record_data)
                        
                        # TLV format: 0x03 (NDEF) + length + NDEF message + 0xFE (terminator)
                        ndef_data = [0x03, total_length] + ndef_header + record_data + [0xFE]
                        
                        # Initialize NDEF capability
                        init_command = [0xFF, 0xD6, 0x00, 0x03, 0x04, 0xE1, 0x10, 0x06, 0x0F]
                        response, sw1, sw2 = connection.transmit(init_command)
                        if sw1 != 0x90:
                            raise Exception(f"NDEF initialization failed: {sw1:02X} {sw2:02X}")
                        
                        # Write data in chunks of 4 bytes (one page at a time)
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
                                raise Exception(f"Failed to write page {page}")

                        # Lock the tag if requested
                        if self.lock_var.get():
                            response, sw1, sw2 = connection.transmit(self.LOCK_CARD)
                            if sw1 != 0x90:
                                raise Exception("Failed to lock tag")
                        
                        tags_written += 1
                        self.progress_var.set(
                            f"Progress: {tags_written}/{quantity} tags written")
                        
                        if tags_written == quantity:
                            self.write_status.config(
                                text=f"Successfully wrote {quantity} tags")
                            break
                        else:
                            self.write_status.config(
                                text=f"Wrote tag {tags_written}/{quantity}. Please present next tag.")
                
                connection.disconnect()
                
            except Exception as e:
                error_msg = str(e)
                if not any(msg in error_msg.lower() for msg in [
                    "card is not connected",
                    "no smart card inserted",
                    "card is unpowered"
                ]):
                    self.write_status.config(text=f"Error: {error_msg}")
                    # Don't break on error, continue with next tag
                
            time.sleep(0.2)  # Delay between attempts

    def run(self):
        """Start the GUI application."""
        self.root.mainloop()

if __name__ == "__main__":
    app = NFCReaderGUI()
    app.run()
