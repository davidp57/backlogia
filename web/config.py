# config.py
# Configuration constants for the Backlogia application

import os
from pathlib import Path

# Database path - can be overridden by environment variable
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent.parent / "game_library.db"))
