#!/usr/bin/env python3
"""
Build script for creating an AppImage of the NFC Reader/Writer application.
This script first builds the application using PyInstaller and then packages it as an AppImage.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime


def ensure_dir(directory):
    """Create directory if it doesn't exist and verify it was created."""
    os.makedirs(directory, exist_ok=True)
    if not os.path.exists(directory):
        raise OSError(f"Failed to create directory: {directory}")
    return directory


def main():
    """Main build function for creating an AppImage."""
    # Set base directories
    src_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, 'dist')
    ensure_dir(output_dir)
    
    # Create a timestamp for unique build directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create temporary AppDir structure
    appdir_root = os.path.join(src_dir, 'build', f'AppDir_{timestamp}')
    
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
    
    print("\nStep 2: Creating AppDir structure...")
    
    # Create directory structure - ensure all parent directories are created
    try:
        # Create the basic structure
        ensure_dir(appdir_root)
        
        # Create usr/bin directory
        appdir_bin = ensure_dir(os.path.join(appdir_root, 'usr', 'bin'))
        
        # Create usr/lib directory
        ensure_dir(os.path.join(appdir_root, 'usr', 'lib'))
        
        # Create usr/share/applications directory
        appdir_applications = ensure_dir(os.path.join(appdir_root, 'usr', 'share', 'applications'))
        
        # Create usr/share/icons/hicolor/256x256/apps directory
        appdir_icons_dir = ensure_dir(os.path.join(appdir_root, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps'))
        
        print("AppDir directory structure created successfully")
    except Exception as e:
        print(f"Error creating AppDir structure: {e}")
        return
    
    # Copy the executable to AppDir
    dest_executable = os.path.join(appdir_bin, 'nfc-rw')
    try:
        shutil.copy2(executable_path, dest_executable)
        print(f"Copied executable to {dest_executable}")
        # Make the executable executable
        os.chmod(dest_executable, 0o755)
    except Exception as e:
        print(f"Error copying executable: {e}")
        return
    
    # Copy icon
    icon_path = os.path.join(src_dir, 'launcher-icon', 'icon.png')
    if os.path.exists(icon_path):
        try:
            # Copy to icons directory
            dest_icon = os.path.join(appdir_icons_dir, 'nfc-rw.png')
            shutil.copy2(icon_path, dest_icon)
            print(f"Copied icon to {dest_icon}")
            
            # Copy to root directory (required by AppImage)
            root_icon = os.path.join(appdir_root, 'nfc-rw.png')
            shutil.copy2(icon_path, root_icon)
            print(f"Copied icon to {root_icon}")
        except Exception as e:
            print(f"Error copying icon: {e}")
            return
    else:
        print(f"Warning: Icon not found at {icon_path}")
    
    # Create desktop entry in both locations (root and applications directory)
    desktop_entry_content = """[Desktop Entry]
Type=Application
Name=NFC Reader/Writer
Comment=Read and write NFC tags
Exec=nfc-rw
Icon=nfc-rw
Categories=Utility;
Terminal=false
"""
    
    # Create desktop entry in applications directory
    applications_desktop_entry = os.path.join(appdir_applications, 'nfc-rw.desktop')
    try:
        with open(applications_desktop_entry, 'w') as f:
            f.write(desktop_entry_content)
        print(f"Created desktop entry at {applications_desktop_entry}")
    except Exception as e:
        print(f"Error creating desktop entry in applications directory: {e}")
        return
    
    # Create desktop entry in root directory (required by AppImage)
    root_desktop_entry = os.path.join(appdir_root, 'nfc-rw.desktop')
    try:
        with open(root_desktop_entry, 'w') as f:
            f.write(desktop_entry_content)
        print(f"Created desktop entry at {root_desktop_entry}")
    except Exception as e:
        print(f"Error creating desktop entry in root directory: {e}")
        return
    
    # Create AppRun script
    apprun_path = os.path.join(appdir_root, 'AppRun')
    try:
        with open(apprun_path, 'w') as f:
            f.write("""#!/bin/sh
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/nfc-rw" "$@"
""")
        # Make AppRun executable
        os.chmod(apprun_path, 0o755)
        print(f"Created AppRun script at {apprun_path}")
    except Exception as e:
        print(f"Error creating AppRun script: {e}")
        return
    
    print("\nStep 3: Downloading and using appimagetool...")
    
    # Download appimagetool if not present
    appimagetool_dir = ensure_dir(os.path.join(src_dir, 'build'))
    appimagetool_path = os.path.join(appimagetool_dir, 'appimagetool-x86_64.AppImage')
    
    if not os.path.exists(appimagetool_path):
        download_cmd = [
            'wget', 'https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage',
            '-O', appimagetool_path
        ]
        try:
            print("Downloading appimagetool...")
            subprocess.check_call(download_cmd)
            os.chmod(appimagetool_path, 0o755)
            print("Downloaded appimagetool successfully")
        except subprocess.CalledProcessError:
            print("Failed to download appimagetool.")
            return
    else:
        print(f"Using existing appimagetool at {appimagetool_path}")
    
    # Create the AppImage
    print("\nStep 4: Creating AppImage...")
    appimage_name = f"NFC-Reader-Writer-{timestamp}-x86_64.AppImage"
    appimage_path = os.path.join(output_dir, appimage_name)
    
    # Set environment variables for appimagetool
    env = os.environ.copy()
    env['ARCH'] = 'x86_64'
    
    # Run appimagetool
    appimage_cmd = [
        appimagetool_path,
        appdir_root,
        appimage_path
    ]
    
    try:
        print("Running appimagetool to create AppImage...")
        subprocess.check_call(appimage_cmd, env=env)
        print(f"\nAppImage created successfully at: {appimage_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create AppImage: {e}")
        return
    
    # Clean up
    print("\nStep 5: Cleaning up...")
    if os.path.exists(appdir_root):
        try:
            shutil.rmtree(appdir_root)
            print(f"Removed temporary AppDir: {appdir_root}")
        except Exception as e:
            print(f"Warning: Failed to clean up {appdir_root}: {e}")
    
    print("\nBuild completed successfully!")
    print(f"AppImage created at: {appimage_path}")
    print("You can distribute this file to users who can then run it directly without installation.")


if __name__ == "__main__":
    main()
