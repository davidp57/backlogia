# web package
# Flask app factory for Backlogia

import sqlite3
from flask import Flask

from .config import DATABASE_PATH
from .database import ensure_extra_columns, ensure_collections_tables
from .services.database_builder import create_database
from .services.igdb_sync import add_igdb_columns
from .routes import register_blueprints


def create_app():
    """Flask application factory."""
    app = Flask(__name__)

    # Initialize database
    _init_database()

    # Register all blueprints
    register_blueprints(app)

    return app


def _init_database():
    """Initialize the database and ensure all tables/columns exist."""
    # Ensure database and tables exist
    create_database()
    ensure_extra_columns()
    ensure_collections_tables()

    # Add IGDB columns
    conn = sqlite3.connect(DATABASE_PATH)
    add_igdb_columns(conn)
    conn.close()
