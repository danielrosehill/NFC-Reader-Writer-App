import os
import sys
import venv
import subprocess
from datetime import datetime
import shutil

def setup_venv():
    venv_dir = 'venv'
    if not os.path.exists(venv_dir):
        print("Creating virtual environment...")
        venv.create(venv_dir, with_pip=True)
    
    # Get the path to pip in the virtual environment
    if sys.platform == "win32":
        pip_path = os.path.join(venv_dir, 'Scripts', 'pip')
        python_path = os.path.join(venv_dir, 'Scripts', 'python')
    else:
        pip_path = os.path.join(venv_dir, 'bin', 'pip')
        python_path = os.path.join(venv_dir, 'bin', 'python')
    
    print("Installing requirements...")
    subprocess.check_call([pip_path, 'install', '-r', 'requirements.txt'])
    return python_path

# Create build directory
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
build_dir = os.path.join('build', 'build_{}'.format(timestamp))
os.makedirs(build_dir, exist_ok=True)

# Setup virtual environment and get python path
python_path = setup_venv()

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

# Run PyInstaller through the virtual environment
subprocess.check_call([python_path, '-m', 'PyInstaller'] + args)

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
