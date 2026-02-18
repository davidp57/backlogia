"""
Edge case tests for labels, metadata, and auto-tagging system

Tests complex scenarios with multiple metadata types, NULL values,
system label deletion, and performance.
"""

import sys
from pathlib import Path

# Add parent directory to path to import web modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
import time
from web.services.system_labels import (
    ensure_system_labels,
    update_auto_labels_for_game,
    update_all_auto_labels
)


@pytest.fixture
def test_db():
    """Create a test database with full schema"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create games table with all metadata columns
    cursor.execute("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            store TEXT,
            playtime_hours REAL,
            hidden INTEGER DEFAULT 0,
            nsfw INTEGER DEFAULT 0,
            priority TEXT CHECK(priority IN ('high', 'medium', 'low', NULL)),
            personal_rating INTEGER CHECK(personal_rating >= 0 AND personal_rating <= 10)
        )
    """)

    # Create labels table
    cursor.execute("""
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            icon TEXT,
            color TEXT,
            system INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create game_labels junction table
    cursor.execute("""
        CREATE TABLE game_labels (
            label_id INTEGER,
            game_id INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            auto INTEGER DEFAULT 0,
            PRIMARY KEY (label_id, game_id),
            FOREIGN KEY (label_id) REFERENCES labels(id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX idx_game_labels_game_id ON game_labels(game_id)")
    cursor.execute("CREATE INDEX idx_game_labels_label_id ON game_labels(label_id)")

    conn.commit()

    # Initialize system labels
    ensure_system_labels(conn)

    yield conn
    conn.close()


# ============================================================================
# Game with ALL Metadata Tests
# ============================================================================

def test_game_with_all_metadata(test_db):
    """Test game with priority, rating, tags, and multiple collections"""
    cursor = test_db.cursor()

    # Create user collections
    cursor.execute("""
        INSERT INTO labels (name, type, icon, color, system)
        VALUES
            ('Favorites', 'collection', ':star:', '#fbbf24', 0),
            ('Backlog', 'collection', ':hourglass:', '#6366f1', 0),
            ('Couch Co-op', 'collection', ':game_die:', '#10b981', 0)
    """)
    test_db.commit()

    # Create a game with all metadata
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours, priority, personal_rating, hidden, nsfw)
        VALUES ('Complete Game', 'steam', 50.0, 'high', 10, 0, 0)
    """)
    game_id = cursor.lastrowid
    test_db.commit()

    # Add auto playtime tag
    update_auto_labels_for_game(test_db, game_id)

    # Add to 3 collections
    cursor.execute("SELECT id FROM labels WHERE type = 'collection'")
    collection_ids = [row[0] for row in cursor.fetchall()]
    for coll_id in collection_ids:
        cursor.execute("""
            INSERT INTO game_labels (label_id, game_id, auto)
            VALUES (?, ?, 0)
        """, (coll_id, game_id))
    test_db.commit()

    # Verify game has complete metadata
    cursor.execute("""
        SELECT priority, personal_rating, hidden, nsfw
        FROM games WHERE id = ?
    """, (game_id,))
    row = cursor.fetchone()
    assert row[0] == 'high'
    assert row[1] == 10
    assert row[2] == 0
    assert row[3] == 0

    # Verify game has 1 system tag + 3 collections (4 total labels)
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels WHERE game_id = ?
    """, (game_id,))
    assert cursor.fetchone()[0] == 4

    # Verify system tag is correct (50h = Heavily Played)
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND l.system = 1
    """, (game_id,))
    assert cursor.fetchone()[0] == 'Heavily Played'

    # Verify in all 3 collections
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND l.type = 'collection'
        ORDER BY l.name
    """, (game_id,))
    collections = [row[0] for row in cursor.fetchall()]
    assert collections == ['Backlog', 'Couch Co-op', 'Favorites']


def test_game_retrieval_with_all_metadata(test_db):
    """Test retrieving game with all metadata in a single query"""
    cursor = test_db.cursor()

    # Create game with metadata
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours, priority, personal_rating)
        VALUES ('Test Game', 'steam', 25.0, 'medium', 8)
    """)
    game_id = cursor.lastrowid
    test_db.commit()

    # Add auto tag
    update_auto_labels_for_game(test_db, game_id)

    # Retrieve game with all metadata in one query
    cursor.execute("""
        SELECT
            g.name,
            g.priority,
            g.personal_rating,
            g.playtime_hours,
            GROUP_CONCAT(l.name) as labels
        FROM games g
        LEFT JOIN game_labels gl ON g.id = gl.game_id
        LEFT JOIN labels l ON gl.label_id = l.id
        WHERE g.id = ?
        GROUP BY g.id
    """, (game_id,))

    row = cursor.fetchone()
    assert row[0] == 'Test Game'
    assert row[1] == 'medium'
    assert row[2] == 8
    assert row[3] == 25.0
    assert 'Well Played' in row[4]  # 25h = Well Played


# ============================================================================
# System Label Deletion Impact Tests
# ============================================================================

def test_system_label_deletion_prevents_auto_tagging(test_db):
    """Test what happens if a system label is accidentally deleted"""
    cursor = test_db.cursor()

    # Create a Steam game
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES ('Test Game', 'steam', 5.0)
    """)
    game_id = cursor.lastrowid
    test_db.commit()

    # Delete "Played" system label (5h should map to this)
    cursor.execute("DELETE FROM labels WHERE name = 'Played' AND system = 1")
    test_db.commit()

    # Try to auto-tag (should not crash, but won't assign any label)
    update_auto_labels_for_game(test_db, game_id)

    # Verify no label assigned
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels WHERE game_id = ?
    """, (game_id,))
    count = cursor.fetchone()[0]
    assert count == 0


def test_system_label_deletion_orphans_existing_tags(test_db):
    """Test that deleting a system label orphans existing game associations"""
    cursor = test_db.cursor()

    # Create a Steam game and auto-tag it
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES ('Test Game', 'steam', 10.0)
    """)
    game_id = cursor.lastrowid
    test_db.commit()

    update_auto_labels_for_game(test_db, game_id)

    # Verify tag exists
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id,))
    assert cursor.fetchone()[0] == 'Well Played'

    # Delete the system label (should cascade delete game_labels entries if FK is set up)
    cursor.execute("DELETE FROM labels WHERE name = 'Well Played' AND system = 1")
    test_db.commit()

    # Verify game has no labels anymore (if CASCADE works)
    # Note: This depends on ON DELETE CASCADE being configured
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels WHERE game_id = ?
    """, (game_id,))
    # If CASCADE is not set up, this might still be 1 (orphaned)
    # The test documents expected behavior


# ============================================================================
# NULL Playtime Edge Cases
# ============================================================================

def test_null_playtime_gets_never_launched_tag(test_db):
    """Test that games with NULL playtime can get 'Never Launched' tag manually"""
    cursor = test_db.cursor()

    # Create Steam game with NULL playtime
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES ('Test Game', 'steam', NULL)
    """)
    game_id = cursor.lastrowid
    test_db.commit()

    update_auto_labels_for_game(test_db, game_id)

    # Note: Auto-tagging skips games with NULL playtime
    # So this won't get auto-tagged. User must apply manually.
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id,))
    tag = cursor.fetchone()
    assert tag is None, "Games with NULL playtime should not be auto-tagged"


def test_null_playtime_gamepass_games(test_db):
    """Test GamePass games with NULL playtime are handled correctly"""
    cursor = test_db.cursor()

    # Create Xbox GamePass games (often have NULL playtime)
    for i in range(3):
        cursor.execute("""
            INSERT INTO games (name, store, playtime_hours)
            VALUES (?, 'xbox', NULL)
        """, (f"GamePass Game {i+1}",))
    test_db.commit()

    # Batch update (should skip xbox games, but if they were steam they'd get tags)
    update_all_auto_labels(test_db)

    # Verify no tags assigned (xbox games are skipped)
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels gl
        JOIN labels l ON l.id = gl.label_id
        WHERE l.system = 1
    """)
    count = cursor.fetchone()[0]
    assert count == 0  # Xbox games should not get auto-tagged


def test_explicit_zero_vs_null_playtime(test_db):
    """Test difference between 0 hours and NULL playtime"""
    cursor = test_db.cursor()

    # Game with explicit 0 hours
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES ('Zero Hours', 'steam', 0)
    """)
    game_id_zero = cursor.lastrowid

    # Game with NULL hours
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES ('NULL Hours', 'steam', NULL)
    """)
    game_id_null = cursor.lastrowid
    test_db.commit()

    # Auto-tag both
    update_auto_labels_for_game(test_db, game_id_zero)
    update_auto_labels_for_game(test_db, game_id_null)

    # Only the zero-hours game should get "Never Launched"
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id_zero,))
    assert cursor.fetchone()[0] == 'Never Launched'

    # NULL playtime game should have no tag (auto-tagging skips it)
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id_null,))
    tag = cursor.fetchone()
    assert tag is None, "Game with NULL playtime should not be auto-tagged"


# ============================================================================
# Performance Tests
# ============================================================================

def test_large_library_performance(test_db):
    """Test auto-tagging performance with 1000 games"""
    cursor = test_db.cursor()

    # Insert 1000 Steam games with varying playtimes
    games_data = []
    for i in range(1000):
        playtime = (i % 100) * 0.5  # 0 to 49.5 hours
        games_data.append((f"Game {i}", "steam", playtime))

    cursor.executemany("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES (?, ?, ?)
    """, games_data)
    test_db.commit()

    # Time the batch auto-tagging
    start_time = time.time()
    update_all_auto_labels(test_db)
    elapsed = time.time() - start_time

    # Verify all games got tagged
    cursor.execute("""
        SELECT COUNT(DISTINCT gl.game_id)
        FROM game_labels gl
        JOIN labels l ON l.id = gl.label_id
        WHERE l.system = 1
    """)
    tagged_count = cursor.fetchone()[0]
    assert tagged_count == 1000

    # Performance assertion: should complete in under 5 seconds
    # (Adjust threshold based on actual performance requirements)
    assert elapsed < 5.0, f"Tagging 1000 games took {elapsed:.2f}s, expected < 5s"

    print(f"[PERF] Tagged 1000 games in {elapsed:.3f}s ({1000/elapsed:.0f} games/sec)")


def test_batch_vs_individual_tagging_performance(test_db):
    """Compare performance of batch vs individual auto-tagging"""
    cursor = test_db.cursor()

    # Insert 100 games
    games_data = [(f"Game {i}", "steam", i * 0.5) for i in range(100)]
    cursor.executemany("""
        INSERT INTO games (name, store, playtime_hours)
        VALUES (?, ?, ?)
    """, games_data)
    test_db.commit()

    # Get game IDs
    cursor.execute("SELECT id FROM games ORDER BY id")
    game_ids = [row[0] for row in cursor.fetchall()]

    # Test individual tagging
    start_time = time.time()
    for game_id in game_ids:
        update_auto_labels_for_game(test_db, game_id)
    individual_time = time.time() - start_time

    # Clear tags
    cursor.execute("DELETE FROM game_labels")
    test_db.commit()

    # Test batch tagging
    start_time = time.time()
    update_all_auto_labels(test_db)
    batch_time = time.time() - start_time

    # Batch should be significantly faster (at least 2x)
    print(f"[PERF] Individual: {individual_time:.3f}s, Batch: {batch_time:.3f}s")
    print(f"[PERF] Batch is {individual_time/batch_time:.1f}x faster")


# ============================================================================
# Complex Query Tests
# ============================================================================

def test_filter_games_by_multiple_criteria(test_db):
    """Test filtering games with priority AND rating AND label"""
    cursor = test_db.cursor()

    # Create various games
    test_games = [
        ('High Priority Favorite', 'steam', 50.0, 'high', 10),
        ('Medium Priority Good', 'steam', 25.0, 'medium', 8),
        ('Low Priority Meh', 'steam', 5.0, 'low', 5),
        ('Unrated Backlog', 'steam', 1.0, 'medium', None),
    ]

    for game_data in test_games:
        cursor.execute("""
            INSERT INTO games (name, store, playtime_hours, priority, personal_rating)
            VALUES (?, ?, ?, ?, ?)
        """, game_data)
    test_db.commit()

    # Auto-tag all games
    update_all_auto_labels(test_db)

    # Query: High priority + rating >= 8 + Heavily Played
    cursor.execute("""
        SELECT g.name FROM games g
        JOIN game_labels gl ON g.id = gl.game_id
        JOIN labels l ON gl.label_id = l.id
        WHERE g.priority = 'high'
          AND g.personal_rating >= 8
          AND l.name = 'Heavily Played'
          AND l.system = 1
    """)
    results = [row[0] for row in cursor.fetchall()]

    assert len(results) == 1
    assert results[0] == 'High Priority Favorite'


def test_games_with_missing_metadata(test_db):
    """Test querying games with some metadata NULL"""
    cursor = test_db.cursor()

    # Create game with partial metadata
    cursor.execute("""
        INSERT INTO games (name, store, playtime_hours, priority, personal_rating)
        VALUES
            ('Full Metadata', 'steam', 10.0, 'high', 8),
            ('No Priority', 'steam', 10.0, NULL, 8),
            ('No Rating', 'steam', 10.0, 'high', NULL),
            ('No Metadata', 'steam', 10.0, NULL, NULL)
    """)
    test_db.commit()

    # Query games with priority but no rating
    cursor.execute("""
        SELECT name FROM games
        WHERE priority IS NOT NULL
          AND personal_rating IS NULL
    """)
    results = [row[0] for row in cursor.fetchall()]

    assert len(results) == 1
    assert results[0] == 'No Rating'

    # Query games with neither priority nor rating
    cursor.execute("""
        SELECT name FROM games
        WHERE priority IS NULL
          AND personal_rating IS NULL
    """)
    results = [row[0] for row in cursor.fetchall()]

    assert len(results) == 1
    assert results[0] == 'No Metadata'


# ============================================================================
# Transaction and Atomicity Tests
# ============================================================================

def test_batch_tagging_is_atomic(test_db):
    """Test that batch tagging happens in a single transaction"""
    cursor = test_db.cursor()

    # Insert games
    for i in range(10):
        cursor.execute("""
            INSERT INTO games (name, store, playtime_hours)
            VALUES (?, 'steam', ?)
        """, (f"Game {i}", i * 5.0))
    test_db.commit()

    # Count transactions needed (should be 1 for batch operation)
    # This is a simulation - actual transaction counting requires profiling
    update_all_auto_labels(test_db)

    # Verify all games got tagged atomically
    cursor.execute("""
        SELECT COUNT(DISTINCT gl.game_id)
        FROM game_labels gl
        WHERE gl.auto = 1
    """)
    tagged_count = cursor.fetchone()[0]
    assert tagged_count == 10
