# database.py
# Database connection and migration functions

import sqlite3
from .config import DATABASE_PATH


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_extra_columns():
    """Add extra columns to database if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    # Check if games table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if not cursor.fetchone():
        conn.close()
        return  # Table doesn't exist yet, nothing to migrate
    cursor.execute("PRAGMA table_info(games)")
    columns = {row[1] for row in cursor.fetchall()}
    if "hidden" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN hidden BOOLEAN DEFAULT 0")
    if "nsfw" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN nsfw BOOLEAN DEFAULT 0")
    if "cover_url_override" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN cover_url_override TEXT")
    conn.commit()
    conn.close()


def ensure_collections_tables():
    """Create collections tables if they don't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_games (
            collection_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (collection_id, game_id),
            FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def ensure_predefined_query_indexes():
    """Create indexes for predefined query filters to optimize performance."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if games table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if not cursor.fetchone():
        conn.close()
        return  # Table doesn't exist yet, nothing to migrate
    
    # Create indexes for frequently filtered columns
    # These improve performance for predefined query filters
    indexes = [
        ("idx_games_playtime", "CREATE INDEX IF NOT EXISTS idx_games_playtime ON games(playtime_hours)"),
        ("idx_games_total_rating", "CREATE INDEX IF NOT EXISTS idx_games_total_rating ON games(total_rating)"),
        ("idx_games_added_at", "CREATE INDEX IF NOT EXISTS idx_games_added_at ON games(added_at)"),
        ("idx_games_release_date", "CREATE INDEX IF NOT EXISTS idx_games_release_date ON games(release_date)"),
        ("idx_games_nsfw", "CREATE INDEX IF NOT EXISTS idx_games_nsfw ON games(nsfw)"),
        ("idx_games_hidden", "CREATE INDEX IF NOT EXISTS idx_games_hidden ON games(hidden)"),
        ("idx_games_updated_at", "CREATE INDEX IF NOT EXISTS idx_games_updated_at ON games(updated_at)"),
        ("idx_games_aggregated_rating", "CREATE INDEX IF NOT EXISTS idx_games_aggregated_rating ON games(aggregated_rating)"),
        ("idx_games_total_rating_count", "CREATE INDEX IF NOT EXISTS idx_games_total_rating_count ON games(total_rating_count)"),
    ]
    
    for index_name, create_statement in indexes:
        try:
            cursor.execute(create_statement)
        except sqlite3.OperationalError:
            # Index might already exist or column doesn't exist yet
            pass
    
    conn.commit()
    conn.close()


def ensure_popularity_cache_table():
    """Create popularity cache table to store IGDB popularity data."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS popularity_cache (
            igdb_id INTEGER NOT NULL,
            popularity_type INTEGER NOT NULL,
            popularity_value INTEGER NOT NULL,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (igdb_id, popularity_type)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_popularity_cache_type_value 
        ON popularity_cache(popularity_type, popularity_value DESC)
    """)
    
    conn.commit()
    conn.close()


def ensure_news_and_status_tables():
    """Create news and status tracking tables and add related columns to games table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if games table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if not cursor.fetchone():
        conn.close()
        return  # Table doesn't exist yet, nothing to migrate
    
    # Add columns to games table
    cursor.execute("PRAGMA table_info(games)")
    columns = {row[1] for row in cursor.fetchall()}
    
    if "development_status" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN development_status TEXT")
    if "game_version" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN game_version TEXT")
    if "status_last_synced" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN status_last_synced TIMESTAMP")
        print("[DB] Added column: status_last_synced")
    
    # Add news_last_checked column if it doesn't exist
    if "news_last_checked" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN news_last_checked TIMESTAMP")
        print("[DB] Added column: news_last_checked")
    
    # Commit column additions before creating tables
    conn.commit()
    
    # Create game_news table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            author TEXT,
            url TEXT,
            published_at TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes for game_news
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_game_news_game_id 
        ON game_news(game_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_game_news_published_at 
        ON game_news(published_at DESC)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_game_news_url 
        ON game_news(url)
    """)
    
    # Create game_depot_updates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_depot_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            depot_id TEXT,
            manifest_id TEXT,
            update_timestamp TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes for game_depot_updates
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_game_depot_updates_game_id 
        ON game_depot_updates(game_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_game_depot_updates_timestamp 
        ON game_depot_updates(update_timestamp DESC)
    """)
    
    # Create indexes on games table for new columns
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_development_status 
        ON games(development_status)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_games_last_modified 
        ON games(last_modified)
    """)
    
    conn.commit()
    conn.close()
