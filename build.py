#!/usr/bin/env python3
"""
Build script for NFC Reader/Writer application.
Creates a standalone executable using PyInstaller.
"""

import os
import sys
import subprocess
from datetime import datetime
import shutil

def main():
    """Main build function."""
    # Set output directory within the repository
    src_dir = os.path.abspath(os.path.dirname(__file__))
    output_dir = os.path.join(src_dir, 'dist')
    os.makedirs(output_dir, exist_ok=True)
    
    # Create temporary build directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_build_dir = os.path.join('build', f'build_{timestamp}')
    os.makedirs(temp_build_dir, exist_ok=True)
    
    # Ensure source paths are absolute
    src_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Define resources to include
    resources = [
        # Main icon
        (os.path.join(src_dir, 'launcher-icon', 'acr_1252.ico'), 'launcher-icon'),
        (os.path.join(src_dir, 'launcher-icon', 'icon.png'), 'launcher-icon'),
        # Images
        (os.path.join(src_dir, 'images', 'acr_1252.png'), 'images'),
    ]
    
    # Create data arguments for PyInstaller
    data_args = []
    for resource_path, dest_dir in resources:
        data_args.extend(['--add-data', f'{resource_path}{os.pathsep}{dest_dir}'])
    
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
    
    # Run PyInstaller using the current Python interpreter
    print("Running PyInstaller with the following arguments:")
    print(" ".join([sys.executable] + args))
    subprocess.check_call([sys.executable] + args)
    
    # Move executable to final location
    executable = 'nfc-rw' + ('.exe' if sys.platform == 'win32' else '')
    temp_executable_path = os.path.join(temp_build_dir, executable)
    final_executable_path = os.path.join(output_dir, executable)
    
    if os.path.exists(temp_executable_path):
        # Move executable to final location
        shutil.move(temp_executable_path, final_executable_path)
        print('\nBuild completed successfully!')
        print(f'Executable created at: {final_executable_path}')
        
        # Clean up all temporary files
        if os.path.exists('build'):
            shutil.rmtree('build')
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
    else:
        print('\nError: Build failed to create executable')

if __name__ == "__main__":
    main()
