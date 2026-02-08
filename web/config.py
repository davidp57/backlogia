# config.py
# Configuration constants for the Backlogia application

import os
import sys
from pathlib import Path


def get_data_dir():
    """Get the data directory for storing database and settings.
    
    When running as a PyInstaller executable, use a persistent location
    in the user's home directory. Otherwise, use the project directory.
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - use user data directory
        if sys.platform == 'win32':
            # Windows: %APPDATA%\Backlogia
            data_dir = Path(os.environ.get('APPDATA', Path.home())) / 'Backlogia'
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Application Support/Backlogia
            data_dir = Path.home() / 'Library' / 'Application Support' / 'Backlogia'
        else:
            # Linux: ~/.local/share/backlogia
            data_dir = Path.home() / '.local' / 'share' / 'backlogia'
    else:
        # Running from source - use project directory
        data_dir = Path(__file__).parent.parent

    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# Database path - can be overridden by environment variable
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", get_data_dir() / "game_library.db"))

# Feature flags - Steam Client integration
# Will be dynamically checked from settings at runtime
def get_use_steam_client():
    """Get USE_STEAM_CLIENT setting from DB or env var."""
    # Check env var first (for Docker)
    env_value = os.environ.get("USE_STEAM_CLIENT", "").strip().lower()
    if env_value in ("true", "1", "yes"):
        return True
    if env_value in ("false", "0", "no"):
        return False
    
    # Fall back to database setting
    try:
        from .services.settings import get_setting, USE_STEAM_CLIENT as USE_STEAM_CLIENT_KEY
        return get_setting(USE_STEAM_CLIENT_KEY, "false").lower() in ("true", "1", "yes")
    except Exception:
        return False

USE_STEAM_CLIENT = get_use_steam_client()
