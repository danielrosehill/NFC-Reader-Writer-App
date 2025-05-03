#!/usr/bin/env python3
"""
Build script for creating a Debian package (.deb) of the NFC Reader/Writer application.
This script first builds the application using PyInstaller and then packages it as a .deb file.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime
import platform

def ensure_dir(directory):
    """Create directory if it doesn't exist and verify it was created."""
    os.makedirs(directory, exist_ok=True)
    if not os.path.exists(directory):
        raise OSError(f"Failed to create directory: {directory}")
    return directory

def main():
    """Main build function for creating a Debian package."""
    # Check if running on a Debian-based system
    if not os.path.exists('/usr/bin/dpkg-deb'):
        print("Error: This script requires dpkg-deb, which is not installed.")
        print("Please run: sudo apt-get install dpkg-dev")
        return

    # Set base directories
    src_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, 'dist')
    ensure_dir(output_dir)
    
    # Create a timestamp for unique build directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Get version information
    version = "1.0.0"  # Default version
    try:
        # You could read this from a version file if you have one
        pass
    except:
        print(f"Using default version: {version}")

    # Package name
    package_name = "nfc-reader-writer"
    
    # Architecture
    arch = "amd64"  # For x86_64 systems
    if platform.machine() == 'aarch64' or platform.machine() == 'arm64':
        arch = "arm64"
    
    # Create temporary build directory for the Debian package
    deb_root = os.path.join(src_dir, 'build', f'deb_{timestamp}')
    
    # First, build the application using PyInstaller
    print("\nStep 1: Building application with PyInstaller...")
    
    # Use virtual environment Python if available
    python_executable = sys.executable
    venv_python = os.path.join(src_dir, '.venv', 'bin', 'python')
    if os.path.exists(venv_python):
        python_executable = venv_python
        print(f"Using virtual environment Python: {venv_python}")
    
    # Build the application
    build_cmd = [
        python_executable, 'build.py'
    ]
    
    try:
        subprocess.check_call(build_cmd)
    except subprocess.CalledProcessError:
        print("Failed to build the application with PyInstaller.")
        return
    
    # Check if the executable was created
    executable_path = os.path.join(src_dir, 'dist', 'nfc-rw')
    if not os.path.exists(executable_path):
        print(f"Error: Executable not found at {executable_path}")
        return
    
    print("\nStep 2: Creating Debian package structure...")
    
    # Create directory structure for Debian package
    try:
        # Main package directory
        ensure_dir(deb_root)
        
        # DEBIAN control directory
        debian_dir = ensure_dir(os.path.join(deb_root, 'DEBIAN'))
        
        # usr/bin directory for the executable
        bin_dir = ensure_dir(os.path.join(deb_root, 'usr', 'bin'))
        
        # usr/share/applications for .desktop file
        applications_dir = ensure_dir(os.path.join(deb_root, 'usr', 'share', 'applications'))
        
        # usr/share/icons/hicolor/256x256/apps for icon
        icons_dir = ensure_dir(os.path.join(deb_root, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps'))
        
        # usr/share/doc/nfc-reader-writer for documentation
        doc_dir = ensure_dir(os.path.join(deb_root, 'usr', 'share', 'doc', package_name))
        
        print("Debian package directory structure created successfully")
    except Exception as e:
        print(f"Error creating Debian package structure: {e}")
        return
    
    # Copy the executable to the bin directory
    try:
        dest_executable = os.path.join(bin_dir, 'nfc-reader-writer')
        shutil.copy2(executable_path, dest_executable)
        os.chmod(dest_executable, 0o755)
        print(f"Copied executable to {dest_executable}")
    except Exception as e:
        print(f"Error copying executable: {e}")
        return
    
    # Copy icon
    icon_path = os.path.join(src_dir, 'launcher-icon', 'icon.png')
    if os.path.exists(icon_path):
        try:
            dest_icon = os.path.join(icons_dir, 'nfc-reader-writer.png')
            shutil.copy2(icon_path, dest_icon)
            print(f"Copied icon to {dest_icon}")
        except Exception as e:
            print(f"Error copying icon: {e}")
            return
    else:
        print(f"Warning: Icon not found at {icon_path}")
    
    # Create .desktop file
    desktop_entry_content = """[Desktop Entry]
Type=Application
Name=NFC Reader/Writer
Comment=Read and write NFC tags
Exec=nfc-reader-writer
Icon=nfc-reader-writer
Categories=Utility;
Terminal=false
"""
    
    try:
        desktop_file = os.path.join(applications_dir, 'nfc-reader-writer.desktop')
        with open(desktop_file, 'w') as f:
            f.write(desktop_entry_content)
        print(f"Created desktop entry at {desktop_file}")
    except Exception as e:
        print(f"Error creating desktop entry: {e}")
        return
    
    # Create copyright file
    try:
        copyright_file = os.path.join(doc_dir, 'copyright')
        with open(copyright_file, 'w') as f:
            f.write("""NFC Reader/Writer Application

Copyright (c) 2023-2025 Daniel Rosehill

This software is licensed under the MIT License.
""")
        print(f"Created copyright file at {copyright_file}")
    except Exception as e:
        print(f"Error creating copyright file: {e}")
        return
    
    # Create changelog file
    try:
        changelog_file = os.path.join(doc_dir, 'changelog.gz')
        with open(os.path.join(doc_dir, 'changelog'), 'w') as f:
            f.write(f"""nfc-reader-writer ({version}) stable; urgency=low

  * Initial release.

 -- Daniel Rosehill <your.email@example.com>  {datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}
""")
        # Compress the changelog
        subprocess.check_call(['gzip', '-9', '-n', os.path.join(doc_dir, 'changelog')])
        print(f"Created changelog file at {changelog_file}")
    except Exception as e:
        print(f"Error creating changelog file: {e}")
        return
    
    # Create control file
    control_content = f"""Package: {package_name}
Version: {version}
Section: utils
Priority: optional
Architecture: {arch}
Depends: libpcsclite1, libpcsclite-dev, swig
Maintainer: Daniel Rosehill <your.email@example.com>
Description: NFC Reader/Writer Application
 A user-friendly application for reading and writing NFC tags
 using the ACR1252U reader. Perfect for managing URL tags,
 text records, and batch operations.
"""
    
    try:
        control_file = os.path.join(debian_dir, 'control')
        with open(control_file, 'w') as f:
            f.write(control_content)
        print(f"Created control file at {control_file}")
    except Exception as e:
        print(f"Error creating control file: {e}")
        return
    
    # Create postinst script to set up permissions
    try:
        postinst_file = os.path.join(debian_dir, 'postinst')
        with open(postinst_file, 'w') as f:
            f.write("""#!/bin/sh
# postinst script for nfc-reader-writer

set -e

# Add users to the required groups for NFC access
if getent group pcscd >/dev/null; then
    echo "Adding users to pcscd group for NFC access"
    for user in $(getent passwd | grep -E '/home/[^:]+' | cut -d: -f1); do
        if id -nG "$user" | grep -qw "pcscd"; then
            echo "User $user already in pcscd group"
        else
            adduser "$user" pcscd || echo "Failed to add $user to pcscd group"
        fi
    done
fi

# Update icon cache
if command -v update-icon-caches >/dev/null; then
    update-icon-caches /usr/share/icons/hicolor
fi

# Update desktop database
if command -v update-desktop-database >/dev/null; then
    update-desktop-database -q /usr/share/applications
fi

exit 0
""")
        os.chmod(postinst_file, 0o755)
        print(f"Created postinst script at {postinst_file}")
    except Exception as e:
        print(f"Error creating postinst script: {e}")
        return
    
    # Build the Debian package
    print("\nStep 3: Building Debian package...")
    
    deb_filename = f"{package_name}_{version}_{arch}.deb"
    deb_path = os.path.join(output_dir, deb_filename)
    
    try:
        subprocess.check_call(['dpkg-deb', '--build', '--root-owner-group', deb_root, deb_path])
        print(f"\nDebian package created successfully at: {deb_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to build Debian package: {e}")
        return
    
    # Verify the package
    print("\nStep 4: Verifying Debian package...")
    try:
        subprocess.check_call(['dpkg-deb', '-I', deb_path])
        print("\nPackage information looks good.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to verify package: {e}")
    
    # Clean up
    print("\nStep 5: Cleaning up...")
    if os.path.exists(deb_root):
        try:
            shutil.rmtree(deb_root)
            print(f"Removed temporary build directory: {deb_root}")
        except Exception as e:
            print(f"Warning: Failed to clean up {deb_root}: {e}")
    
    print("\nBuild completed successfully!")
    print(f"Debian package created at: {deb_path}")
    print("You can install this package with: sudo dpkg -i " + deb_path)
    print("Or distribute it to other Ubuntu/Debian users.")

if __name__ == "__main__":
    main()