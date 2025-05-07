#!/usr/bin/env python3
import os
import sys
import venv
import subprocess
import shutil
from pathlib import Path

def create_venv():
    """Create a virtual environment if it doesn't exist."""
    print("Creating virtual environment...")
    venv.create("venv", with_pip=True)
    return True

def get_venv_python():
    """Get the path to the virtual environment's Python executable."""
    if sys.platform == "win32":
        return os.path.join("venv", "Scripts", "python.exe")
    return os.path.join("venv", "bin", "python")

def get_venv_pip():
    """Get the path to the virtual environment's pip executable."""
    if sys.platform == "win32":
        return os.path.join("venv", "Scripts", "pip.exe")
    return os.path.join("venv", "bin", "pip")

def install_requirements():
    """Install required packages using pip."""
    print("Installing requirements...")
    pip = get_venv_pip()
    try:
        subprocess.check_call([pip, "install", "-r", "requirements.txt"])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def setup_config():
    """Create config.py if it doesn't exist."""
    if os.path.exists("config.py"):
        print("config.py already exists, skipping...")
        return True
    
    print("Creating config.py...")
    try:
        shutil.copy("example.config.py", "config.py")
        print("\nPlease edit config.py with your settings:")
        print("- Set SIP_USER to your extension")
        print("- Set SIP_PASSWORD to your password")
        print("- Set SIP_DOMAIN to your PBX server")
        print("- Set PIXELEBBE_URL to your server URL")
        return True
    except Exception as e:
        print(f"Error creating config.py: {e}")
        return False

def main():
    """Main setup function."""
    print("Starting setup for pixelebbe phone tree handler...")
    
    # Create virtual environment
    if not create_venv():
        print("Failed to create virtual environment")
        return False
    
    # Install requirements
    if not install_requirements():
        print("Failed to install requirements")
        return False
    
    # Setup config
    if not setup_config():
        print("Failed to setup config")
        return False
    
    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("1. Edit config.py with your settings")
    print("\nTo run the service:")
    if sys.platform == "win32":
        print("   .\\venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    print("   python py_voip_client.py")
    
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1) 