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

# Set output directory
output_dir = '/home/daniel/Programs/created/nfc-reader-writer/new-builds'
os.makedirs(output_dir, exist_ok=True)

# Create temporary build directory
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
temp_build_dir = os.path.join('build', 'build_{}'.format(timestamp))
os.makedirs(temp_build_dir, exist_ok=True)

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
    '--workpath', os.path.join(temp_build_dir, 'temp'),
    '--specpath', os.path.join(temp_build_dir, 'temp'),
    # Output directory
    '--distpath', temp_build_dir,
]

# Run PyInstaller through the virtual environment
subprocess.check_call([python_path, '-m', 'PyInstaller'] + args)

# Move executable to final location
executable = 'nfc-rw' + ('.exe' if sys.platform == 'win32' else '')
temp_executable_path = os.path.join(temp_build_dir, executable)
final_executable_path = os.path.join(output_dir, executable)

if os.path.exists(temp_executable_path):
    # Move executable to final location
    shutil.move(temp_executable_path, final_executable_path)
    print('\nBuild completed successfully!')
    print('Executable created at: {}'.format(final_executable_path))
    
    # Clean up all temporary files
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('__pycache__'):
        shutil.rmtree('__pycache__')
    spec_file = 'nfc-rw.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
else:
    print('\nError: Build failed to create executable')
