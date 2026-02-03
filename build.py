"""
Build script for creating Backlogia desktop executable
"""

import sys
import shutil
import subprocess
from pathlib import Path
import importlib.util

def check_pyinstaller():
    """Check if PyInstaller is installed."""
    if importlib.util.find_spec("PyInstaller") is not None:
        print("[OK] PyInstaller is installed")
        return True
    else:
        print("[FAIL] PyInstaller is not installed")
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements-build.txt"])
        return True

def clean_build():
    """Remove previous build artifacts."""
    print("[OK] Cleaning previous build artifacts...")
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"[OK] Removed {dir_name}/")

def build_executable():
    """Build the executable using PyInstaller."""
    print("[OK] Building executable...")
    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller", "backlogia.spec"])
        print("[OK] Build completed successfully!")
        print(f"[OK] Executable location: {Path('dist/Backlogia').absolute()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] Build failed: {e}")
        return False

def main():
    """Main build process."""
    print("=" * 60)
    print("Backlogia Desktop Build Script")
    print("=" * 60)

    # Check dependencies
    if not check_pyinstaller():
        sys.exit(1)

    # Clean previous builds
    clean_build()

    # Build executable
    if not build_executable():
        sys.exit(1)

    print("=" * 60)
    print("[OK] Build process complete!")
    print("[OK] Run the application: dist\\Backlogia\\Backlogia.exe")
    print("=" * 60)

if __name__ == "__main__":
    main()
