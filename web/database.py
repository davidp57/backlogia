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


def migrate_collections_to_labels():
    """Migrate collections table to labels with additional fields."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check if migration is needed
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='labels'")
    if cursor.fetchone():
        conn.close()
        return  # Already migrated

    # Check if collections table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collections'")
    if not cursor.fetchone():
        conn.close()
        return  # No collections to migrate, will create labels table directly

    try:
        # Create new labels table with additional fields
        cursor.execute("""
            CREATE TABLE labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL DEFAULT 'collection',
                color TEXT,
                icon TEXT,
                system INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Copy data from collections to labels
        cursor.execute("""
            INSERT INTO labels (id, name, description, created_at, updated_at)
            SELECT id, name, description, created_at, updated_at FROM collections
        """)

        # Create new game_labels junction table
        cursor.execute("""
            CREATE TABLE game_labels (
                label_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auto INTEGER DEFAULT 0,
                PRIMARY KEY (label_id, game_id),
                FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE,
                FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
            )
        """)

        # Copy data from collection_games to game_labels
        cursor.execute("""
            INSERT INTO game_labels (label_id, game_id, added_at)
            SELECT collection_id, game_id, added_at FROM collection_games
        """)

        # Drop old tables
        cursor.execute("DROP TABLE collection_games")
        cursor.execute("DROP TABLE collections")

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_labels_game_id ON game_labels(game_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_labels_label_id ON game_labels(label_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_type ON labels(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_system ON labels(system)")

        conn.commit()
        print("[OK] Collections successfully migrated to labels")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error migrating collections to labels: {e}")
    finally:
        conn.close()


def ensure_labels_tables():
    """Create labels tables if they don't exist (replaces ensure_collections_tables)."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Create labels table (new unified system)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL DEFAULT 'collection',
            color TEXT,
            icon TEXT,
            system INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create game_labels junction table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_labels (
            label_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto INTEGER DEFAULT 0,
            PRIMARY KEY (label_id, game_id),
            FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_labels_game_id ON game_labels(game_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_labels_label_id ON game_labels(label_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_type ON labels(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_labels_system ON labels(system)")

    conn.commit()
    conn.close()


def ensure_game_metadata_columns():
    """Add priority and personal_rating columns to games table."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Check if games table exists first
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'")
    if not cursor.fetchone():
        conn.close()
        return  # Table doesn't exist yet, nothing to migrate

    # Check existing columns
    cursor.execute("PRAGMA table_info(games)")
    columns = {row[1] for row in cursor.fetchall()}

    # Add priority column
    if "priority" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN priority TEXT CHECK(priority IN ('high', 'medium', 'low', NULL))")
        print("[OK] Added priority column to games table")

    # Add personal_rating column
    if "personal_rating" not in columns:
        cursor.execute("ALTER TABLE games ADD COLUMN personal_rating INTEGER CHECK(personal_rating >= 0 AND personal_rating <= 10)")
        print("[OK] Added personal_rating column to games table")

    # Create index for personal_rating
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_games_personal_rating ON games(personal_rating)")
    except sqlite3.OperationalError:
        pass  # Index might already exist

    conn.commit()
    conn.close()
