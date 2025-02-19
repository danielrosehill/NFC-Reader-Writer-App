import os
import sys
from datetime import datetime
import PyInstaller.__main__
import shutil

# Create build directory
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
build_dir = os.path.join('build', 'build_{}'.format(timestamp))
os.makedirs(build_dir, exist_ok=True)

# Ensure source paths are absolute
src_dir = os.path.abspath(os.path.dirname(__file__))
image_path = os.path.join(src_dir, 'images', 'acr_1252.png')

# Define PyInstaller arguments
args = [
    'latest.py',
    '--onefile',  # Create a single executable
    '--clean',    # Clean PyInstaller cache
    '--name', 'nfc-rw',
    # Bundle the image file with absolute path
    '--add-data', '{}{}'.format(image_path, os.pathsep + 'images'),
    # Temporary directories for build process
    '--workpath', os.path.join(build_dir, 'temp'),
    '--specpath', os.path.join(build_dir, 'temp'),
    # Output directory
    '--distpath', build_dir,
]

# Run PyInstaller
PyInstaller.__main__.run(args)

# Clean up temporary directories
temp_dir = os.path.join(build_dir, 'temp')
if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)

# Move executable to final location
executable = 'nfc-rw' + ('.exe' if sys.platform == 'win32' else '')
executable_path = os.path.join(build_dir, executable)

if os.path.exists(executable_path):
    print('\nBuild completed successfully!')
    print('Executable created at: {}'.format(executable_path))
else:
    print('\nError: Build failed to create executable')
