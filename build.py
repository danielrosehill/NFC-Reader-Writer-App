import os
import sys
from datetime import datetime
import PyInstaller.__main__
import shutil

# Create timestamped build directory
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
build_dir = os.path.join('build', f'build_{timestamp}')
os.makedirs(build_dir, exist_ok=True)

# Define PyInstaller arguments
args = [
    'latest.py',
    '--onefile',
    '--clean',
    '--distpath', build_dir,
    '--workpath', os.path.join(build_dir, 'work'),
    '--specpath', build_dir,
    '--add-data', f'images/acr_1252.png{os.pathsep}images',
    '--name', 'nfc-rw'
]

# Ensure the image directory exists in the build directory
os.makedirs(os.path.join(build_dir, 'images'), exist_ok=True)
shutil.copy2('images/acr_1252.png', os.path.join(build_dir, 'images'))

# Run PyInstaller
PyInstaller.__main__.run(args)

print(f'\nBuild completed successfully in: {build_dir}')
