#!/usr/bin/env python3
"""
Consolidated build script for NFC Reader/Writer application.
Creates a standalone executable using PyInstaller and optionally packages it as:
- Debian package (.deb)
- AppImage (.AppImage)
"""

import os
import sys
import subprocess
import shutil
import argparse
from datetime import datetime
import platform


def ensure_dir(directory):
    """Create directory if it doesn't exist and verify it was created."""
    os.makedirs(directory, exist_ok=True)
    if not os.path.exists(directory):
        raise OSError(f"Failed to create directory: {directory}")
    return directory


def build_executable():
    """Build the executable using PyInstaller."""
    print("\nStep 1: Building application with PyInstaller...")
    
    # Set output directory within the repository
    src_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, 'dist')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create temporary build directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_build_dir = os.path.join('build', f'build_{timestamp}')
    os.makedirs(temp_build_dir, exist_ok=True)
    os.makedirs(os.path.join(temp_build_dir, 'temp'), exist_ok=True)
    
    # Define resources to include
    resources = [
        # Main icon
        (os.path.join(src_dir, 'launcher-icon', 'acr_1252.ico'), 'launcher-icon'),
        (os.path.join(src_dir, 'launcher-icon', 'icon.png'), 'launcher-icon'),
        # Images
        (os.path.join(src_dir, 'images', 'acr_1252.png'), 'images'),
    ]
    
    # Verify all resources exist
    for resource_path, _ in resources:
        if not os.path.exists(resource_path):
            print(f"Error: Resource not found: {resource_path}")
            return False
    
    # Create data arguments for PyInstaller
    data_args = []
    for resource_path, dest_dir in resources:
        data_args.extend(['--add-data', f'{resource_path}{os.pathsep}{dest_dir}'])
    
    # Use virtual environment Python if available
    python_executable = sys.executable
    venv_python = os.path.join(src_dir, '.venv', 'bin', 'python')
    if os.path.exists(venv_python):
        python_executable = venv_python
        print(f"Using virtual environment Python: {venv_python}")
    
    # Define PyInstaller arguments
    args = [
        '-m', 'PyInstaller',
        'run.py',                          # New entry point
        '--onefile',                       # Create a single executable
        '--clean',                         # Clean PyInstaller cache
        '--name', 'nfc-rw',
        '--hidden-import', 'app',          # Include app package
        '--hidden-import', 'app.ui',       # Include UI subpackage
        '--hidden-import', 'app.main',     # Include main module
        '--hidden-import', 'app.gui',      # Include GUI module
        '--hidden-import', 'app.reader',   # Include reader module
        '--hidden-import', 'app.writer',   # Include writer module
        '--hidden-import', 'app.copier',   # Include copier module
        '--hidden-import', 'app.utils',    # Include utils module
        # Add data resources
        *data_args,
        # Temporary directories for build process
        '--workpath', os.path.join(temp_build_dir, 'temp'),
        '--specpath', os.path.join(temp_build_dir, 'temp'),
        # Output directory
        '--distpath', temp_build_dir,
    ]
    
    # Run PyInstaller using the selected Python interpreter
    print(f"Using Python interpreter: {python_executable}")
    print("Running PyInstaller with the following arguments:")
    print(" ".join([python_executable] + args))
    
    try:
        subprocess.check_call([python_executable] + args)
        
        # Move executable to final location
        executable = 'nfc-rw' + ('.exe' if sys.platform == 'win32' else '')
        temp_executable_path = os.path.join(temp_build_dir, executable)
        final_executable_path = os.path.join(output_dir, executable)
        
        if os.path.exists(temp_executable_path):
            # Move executable to final location
            shutil.move(temp_executable_path, final_executable_path)
            print('\nExecutable built successfully!')
            print(f'Executable created at: {final_executable_path}')
            
            # Clean up temporary build files
            if os.path.exists(temp_build_dir):
                shutil.rmtree(temp_build_dir)
            if os.path.exists('__pycache__'):
                shutil.rmtree('__pycache__')
            # Clean up app package pycache
            if os.path.exists(os.path.join('app', '__pycache__')):
                shutil.rmtree(os.path.join('app', '__pycache__'))
            # Clean up app.ui package pycache
            if os.path.exists(os.path.join('app', 'ui', '__pycache__')):
                shutil.rmtree(os.path.join('app', 'ui', '__pycache__'))
            spec_file = 'nfc-rw.spec'
            if os.path.exists(spec_file):
                os.remove(spec_file)
                
            return final_executable_path
        else:
            print(f'\nError: Build failed to create executable at {temp_executable_path}')
            return False
    except subprocess.CalledProcessError as e:
        print(f"\nError: PyInstaller failed with exit code {e.returncode}")
        print("Try running the build with the virtual environment activated:")
        print("source .venv/bin/activate && python build.py")
        return False


def build_deb_package(executable_path):
    """Build a Debian package (.deb) from the executable."""
    print("\nBuilding Debian package...")
    
    # Check if running on a Debian-based system
    if not os.path.exists('/usr/bin/dpkg-deb'):
        print("Error: This script requires dpkg-deb, which is not installed.")
        print("Please run: sudo apt-get install dpkg-dev")
        return False
    
    # Set base directories
    src_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, 'dist')
    
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
    
    print("\nCreating Debian package structure...")
    
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
        return False
    
    # Copy the executable to the bin directory
    try:
        dest_executable = os.path.join(bin_dir, 'nfc-reader-writer')
        shutil.copy2(executable_path, dest_executable)
        os.chmod(dest_executable, 0o755)
        print(f"Copied executable to {dest_executable}")
    except Exception as e:
        print(f"Error copying executable: {e}")
        return False
    
    # Copy icon
    icon_path = os.path.join(src_dir, 'launcher-icon', 'icon.png')
    if os.path.exists(icon_path):
        try:
            dest_icon = os.path.join(icons_dir, 'nfc-reader-writer.png')
            shutil.copy2(icon_path, dest_icon)
            print(f"Copied icon to {dest_icon}")
        except Exception as e:
            print(f"Error copying icon: {e}")
            return False
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
        return False
    
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
        return False
    
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
        return False
    
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
        return False
    
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
        return False
    
    # Build the Debian package
    print("\nBuilding Debian package...")
    
    deb_filename = f"{package_name}_{version}_{arch}.deb"
    deb_path = os.path.join(output_dir, deb_filename)
    
    try:
        subprocess.check_call(['dpkg-deb', '--build', '--root-owner-group', deb_root, deb_path])
        print(f"\nDebian package created successfully at: {deb_path}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to build Debian package: {e}")
        return False
    
    # Verify the package
    print("\nVerifying Debian package...")
    try:
        subprocess.check_call(['dpkg-deb', '-I', deb_path])
        print("\nPackage information looks good.")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to verify package: {e}")
    
    # Clean up
    print("\nCleaning up Debian build files...")
    if os.path.exists(deb_root):
        try:
            shutil.rmtree(deb_root)
            print(f"Removed temporary build directory: {deb_root}")
        except Exception as e:
            print(f"Warning: Failed to clean up {deb_root}: {e}")
    
    print(f"Debian package created at: {deb_path}")
    print("You can install this package with: sudo dpkg -i " + deb_path)
    
    return deb_path


def build_appimage(executable_path):
    """Build an AppImage from the executable."""
    print("\nBuilding AppImage...")
    
    # Set base directories
    src_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, 'dist')
    
    # Create a timestamp for unique build directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create temporary AppDir structure
    appdir_root = os.path.join(src_dir, 'build', f'AppDir_{timestamp}')
    
    print("\nCreating AppDir structure...")
    
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
        return False
    
    # Copy the executable to AppDir
    dest_executable = os.path.join(appdir_bin, 'nfc-rw')
    try:
        shutil.copy2(executable_path, dest_executable)
        print(f"Copied executable to {dest_executable}")
        # Make the executable executable
        os.chmod(dest_executable, 0o755)
    except Exception as e:
        print(f"Error copying executable: {e}")
        return False
    
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
            return False
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
        return False
    
    # Create desktop entry in root directory (required by AppImage)
    root_desktop_entry = os.path.join(appdir_root, 'nfc-rw.desktop')
    try:
        with open(root_desktop_entry, 'w') as f:
            f.write(desktop_entry_content)
        print(f"Created desktop entry at {root_desktop_entry}")
    except Exception as e:
        print(f"Error creating desktop entry in root directory: {e}")
        return False
    
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
        return False
    
    print("\nDownloading and using appimagetool...")
    
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
            return False
    else:
        print(f"Using existing appimagetool at {appimagetool_path}")
    
    # Create the AppImage
    print("\nCreating AppImage...")
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
        return False
    
    # Clean up
    print("\nCleaning up AppImage build files...")
    if os.path.exists(appdir_root):
        try:
            shutil.rmtree(appdir_root)
            print(f"Removed temporary AppDir: {appdir_root}")
        except Exception as e:
            print(f"Warning: Failed to clean up {appdir_root}: {e}")
    
    print(f"AppImage created at: {appimage_path}")
    print("You can distribute this file to users who can then run it directly without installation.")
    
    return appimage_path


def main():
    """Main function to handle command-line arguments and build process."""
    parser = argparse.ArgumentParser(description='Build NFC Reader/Writer application and packages.')
    parser.add_argument('--deb', action='store_true', help='Build Debian package')
    parser.add_argument('--appimage', action='store_true', help='Build AppImage')
    parser.add_argument('--all', action='store_true', help='Build all package formats')
    parser.add_argument('--executable-only', action='store_true', help='Build only the executable')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not (args.deb or args.appimage or args.all or args.executable_only):
        parser.print_help()
        print("\nNo build options specified. Building executable only.")
        args.executable_only = True
    
    # Build the executable first
    executable_path = build_executable()
    if not executable_path:
        print("Failed to build executable. Aborting.")
        return 1
    
    results = []
    
    # Build Debian package if requested
    if args.deb or args.all:
        deb_result = build_deb_package(executable_path)
        if deb_result:
            results.append(f"Debian package: {deb_result}")
        else:
            print("Failed to build Debian package.")
    
    # Build AppImage if requested
    if args.appimage or args.all:
        appimage_result = build_appimage(executable_path)
        if appimage_result:
            results.append(f"AppImage: {appimage_result}")
        else:
            print("Failed to build AppImage.")
    
    # Print summary
    if results:
        print("\nBuild Summary:")
        print(f"Executable: {executable_path}")
        for result in results:
            print(result)
    else:
        print(f"\nBuild completed with executable only: {executable_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
