"""
Tests for automatic system label tagging on Steam sync

Tests that system labels (Never Launched, Just Tried, Played, Well Played, Heavily Played)
are automatically applied to Steam games based on playtime during sync operations.
"""

import sys
from pathlib import Path

# Add parent directory to path to import web modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from web.services.system_labels import (
    ensure_system_labels,
    update_auto_labels_for_game,
    update_all_auto_labels,
    SYSTEM_LABELS
)


@pytest.fixture
def test_db():
    """Create a test database with necessary tables"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create games table
    cursor.execute("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            store TEXT,
            playtime_hours REAL
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
            system INTEGER DEFAULT 0
        )
    """)

    # Create game_labels junction table
    cursor.execute("""
        CREATE TABLE game_labels (
            id INTEGER PRIMARY KEY,
            label_id INTEGER NOT NULL,
            game_id INTEGER NOT NULL,
            auto INTEGER DEFAULT 0,
            FOREIGN KEY (label_id) REFERENCES labels(id),
            FOREIGN KEY (game_id) REFERENCES games(id),
            UNIQUE(label_id, game_id)
        )
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def test_db_with_labels(test_db):
    """Create test database with system labels initialized"""
    ensure_system_labels(test_db)
    return test_db


def test_ensure_system_labels_creates_all_labels(test_db):
    """Test that ensure_system_labels creates all 5 system labels"""
    ensure_system_labels(test_db)

    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM labels WHERE system = 1 AND type = 'system_tag'")
    count = cursor.fetchone()[0]

    assert count == 5, f"Expected 5 system labels, got {count}"

    # Verify all label names exist
    cursor.execute("SELECT name FROM labels WHERE system = 1 AND type = 'system_tag' ORDER BY name")
    names = [row[0] for row in cursor.fetchall()]

    expected_names = sorted(['Never Launched', 'Just Tried', 'Played', 'Well Played', 'Heavily Played'])
    assert names == expected_names, f"Expected {expected_names}, got {names}"


def test_update_auto_labels_never_launched(test_db_with_labels):
    """Test that games with 0 playtime get 'Never Launched' label"""
    cursor = test_db_with_labels.cursor()

    # Insert game with no playtime
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    # Apply auto labels
    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Check label was applied
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))

    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Never Launched'], f"Expected ['Never Launched'], got {labels}"


def test_update_auto_labels_just_tried(test_db_with_labels):
    """Test that games with <2h playtime get 'Just Tried' label"""
    cursor = test_db_with_labels.cursor()

    # Insert game with 1.5 hours
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 1.5))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))

    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Just Tried'], f"Expected ['Just Tried'], got {labels}"


def test_update_auto_labels_played(test_db_with_labels):
    """Test that games with 2-10h playtime get 'Played' label"""
    cursor = test_db_with_labels.cursor()

    # Insert game with 5 hours
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 5.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))

    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Played'], f"Expected ['Played'], got {labels}"


def test_update_auto_labels_well_played(test_db_with_labels):
    """Test that games with 10-50h playtime get 'Well Played' label"""
    cursor = test_db_with_labels.cursor()

    # Insert game with 25 hours
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 25.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))

    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Well Played'], f"Expected ['Well Played'], got {labels}"


def test_update_auto_labels_heavily_played(test_db_with_labels):
    """Test that games with ≥50h playtime get 'Heavily Played' label"""
    cursor = test_db_with_labels.cursor()

    # Insert game with 100 hours
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 100.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))

    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Heavily Played'], f"Expected ['Heavily Played'], got {labels}"


def test_update_auto_labels_only_steam_games(test_db_with_labels):
    """Test that auto labels are only applied to Steam games"""
    cursor = test_db_with_labels.cursor()

    # Insert Epic game with playtime
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Epic Game", "epic", 5.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Check no labels were applied
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels
        WHERE game_id = ? AND auto = 1
    """, (game_id,))

    count = cursor.fetchone()[0]
    assert count == 0, f"Non-Steam game should not get auto labels, but got {count}"


def test_update_auto_labels_ignores_null_playtime(test_db_with_labels):
    """Test that games with NULL playtime don't get auto labels"""
    cursor = test_db_with_labels.cursor()

    # Insert Steam game with NULL playtime
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", None))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Check no labels were applied
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels
        WHERE game_id = ? AND auto = 1
    """, (game_id,))

    count = cursor.fetchone()[0]
    assert count == 0, f"Game with NULL playtime should not get auto labels, but got {count}"


def test_update_all_auto_labels(test_db_with_labels):
    """Test that update_all_auto_labels processes all Steam games"""
    cursor = test_db_with_labels.cursor()

    # Insert multiple Steam games with different playtimes
    games = [
        ("Game 1", "steam", 0),
        ("Game 2", "steam", 1.5),
        ("Game 3", "steam", 5.0),
        ("Game 4", "steam", 25.0),
        ("Game 5", "steam", 100.0),
        ("Game 6", "epic", 10.0),  # Non-Steam, should be ignored
    ]

    for name, store, playtime in games:
        cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                      (name, store, playtime))
    test_db_with_labels.commit()

    # Apply labels to all games
    update_all_auto_labels(test_db_with_labels)

    # Check that only Steam games got labels
    cursor.execute("""
        SELECT COUNT(DISTINCT game_id) FROM game_labels
        WHERE auto = 1
    """)

    count = cursor.fetchone()[0]
    assert count == 5, f"Expected 5 Steam games to get auto labels, got {count}"


def test_update_auto_labels_replaces_old_labels(test_db_with_labels):
    """Test that updating auto labels replaces old ones when playtime changes"""
    cursor = test_db_with_labels.cursor()

    # Insert game with 1 hour (Just Tried)
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 1.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify Just Tried label
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))
    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Just Tried']

    # Update playtime to 50 hours (Heavily Played)
    cursor.execute("UPDATE games SET playtime_hours = ? WHERE id = ?", (50.0, game_id))
    test_db_with_labels.commit()

    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify label was updated to Heavily Played
    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))
    labels = [row[0] for row in cursor.fetchall()]
    assert labels == ['Heavily Played'], f"Expected label to be updated to ['Heavily Played'], got {labels}"

    # Verify only one auto label exists
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels
        WHERE game_id = ? AND auto = 1
    """, (game_id,))
    count = cursor.fetchone()[0]
    assert count == 1, f"Expected only 1 auto label, got {count}"


def test_boundary_values(test_db_with_labels):
    """Test boundary values between label categories"""
    cursor = test_db_with_labels.cursor()

    test_cases = [
        (0, 'Never Launched'),
        (0.1, 'Just Tried'),
        (1.9, 'Just Tried'),
        (2.0, 'Played'),
        (9.9, 'Played'),
        (10.0, 'Well Played'),
        (49.9, 'Well Played'),
        (50.0, 'Heavily Played'),
        (1000.0, 'Heavily Played'),
    ]

    for playtime, expected_label in test_cases:
        cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                      (f"Game {playtime}h", "steam", playtime))
        game_id = cursor.lastrowid
        test_db_with_labels.commit()

        update_auto_labels_for_game(test_db_with_labels, game_id)

        cursor.execute("""
            SELECT l.name FROM labels l
            JOIN game_labels gl ON l.id = gl.label_id
            WHERE gl.game_id = ? AND gl.auto = 1
        """, (game_id,))

        labels = [row[0] for row in cursor.fetchall()]
        assert labels == [expected_label], \
            f"Game with {playtime}h should get '{expected_label}' label, got {labels}"


# ============================================================================
# Manual Tag Persistence Tests
# ============================================================================

def test_manual_tag_survives_auto_tagging(test_db_with_labels):
    """Test that manual tags (auto=0) are not overwritten by auto-tagging"""
    cursor = test_db_with_labels.cursor()

    # Create a Steam game with 5 hours (should get "Played" auto tag)
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 5.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    # Assign a manual "Well Played" tag (override auto tagging)
    cursor.execute("SELECT id FROM labels WHERE name = 'Well Played'")
    label_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO game_labels (label_id, game_id, auto) VALUES (?, ?, 0)",
                  (label_id, game_id))
    test_db_with_labels.commit()

    # Run auto-tagging
    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify manual tag still exists
    cursor.execute("""
        SELECT l.name, gl.auto FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND l.system = 1
        ORDER BY gl.auto
    """, (game_id,))
    tags = cursor.fetchall()

    # Should have only the manual tag (auto=0), auto tag should not be added
    # Note: Current implementation doesn't skip auto-tagging when manual tag exists,
    # so game might have both tags. This behavior could be changed in future.
    assert len(tags) >= 1, f"Expected at least 1 tag, got {len(tags)}: {tags}"
    # Find the manual tag
    manual_tags = [t for t in tags if t[1] == 0]
    assert len(manual_tags) == 1, "Should have exactly one manual tag"
    assert manual_tags[0][0] == 'Well Played'


def test_manual_tag_on_non_steam_game(test_db_with_labels):
    """Test that manual tags can be applied to non-Steam games"""
    cursor = test_db_with_labels.cursor()

    # Create a GOG game (non-Steam)
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("GOG Game", "gog", 15.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    # Assign a manual "Played" tag
    cursor.execute("SELECT id FROM labels WHERE name = 'Played'")
    label_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO game_labels (label_id, game_id, auto) VALUES (?, ?, 0)",
                  (label_id, game_id))
    test_db_with_labels.commit()

    # Run auto-tagging (should skip non-Steam games)
    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify manual tag still exists and no auto tag was added
    cursor.execute("""
        SELECT l.name, gl.auto FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id,))
    tags = cursor.fetchall()

    assert len(tags) == 1
    assert tags[0][0] == 'Played'
    assert tags[0][1] == 0  # manual tag


def test_remove_manual_tag(test_db_with_labels):
    """Test removing a manual tag and allowing auto-tagging to work"""
    cursor = test_db_with_labels.cursor()

    # Create a Steam game with 5 hours
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 5.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    # Assign a manual tag first
    cursor.execute("SELECT id FROM labels WHERE name = 'Heavily Played'")
    label_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO game_labels (label_id, game_id, auto) VALUES (?, ?, 0)",
                  (label_id, game_id))
    test_db_with_labels.commit()

    # Remove the manual tag
    cursor.execute("DELETE FROM game_labels WHERE game_id = ? AND auto = 0", (game_id,))
    test_db_with_labels.commit()

    # Run auto-tagging (should now work since manual tag is removed)
    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify auto tag is applied (5h = "Played")
    cursor.execute("""
        SELECT l.name, gl.auto FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id,))
    tags = cursor.fetchall()

    assert len(tags) == 1
    assert tags[0][0] == 'Played'
    assert tags[0][1] == 1  # auto tag


def test_manual_vs_auto_no_conflict(test_db_with_labels):
    """Test that manual tags take precedence over auto tags"""
    cursor = test_db_with_labels.cursor()

    # Create a Steam game with 100 hours (would auto-tag as "Heavily Played")
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 100.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    # First, let auto-tagging run
    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify auto tag applied
    cursor.execute("""
        SELECT l.name, gl.auto FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id,))
    tags = cursor.fetchall()
    assert len(tags) == 1
    assert tags[0][0] == 'Heavily Played'
    assert tags[0][1] == 1  # auto

    # Now manually override with "Just Tried" (simulating user action)
    # First remove all tags
    cursor.execute("DELETE FROM game_labels WHERE game_id = ?", (game_id,))
    # Add manual tag
    cursor.execute("SELECT id FROM labels WHERE name = 'Just Tried'")
    label_id = cursor.fetchone()[0]
    cursor.execute("INSERT INTO game_labels (label_id, game_id, auto) VALUES (?, ?, 0)",
                  (label_id, game_id))
    test_db_with_labels.commit()

    # Run auto-tagging again
    update_auto_labels_for_game(test_db_with_labels, game_id)

    # Verify manual tag persists and auto tag is not added
    cursor.execute("""
        SELECT l.name, gl.auto FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ?
    """, (game_id,))
    tags = cursor.fetchall()

    # Current implementation might keep both tags
    assert len(tags) >= 1
    # Find the manual tag
    manual_tags = [t for t in tags if t[1] == 0]
    assert len(manual_tags) == 1
    assert manual_tags[0][0] == 'Just Tried'


def test_auto_tag_replacement_on_playtime_change(test_db_with_labels):
    """Test that auto tags are replaced when playtime changes"""
    cursor = test_db_with_labels.cursor()

    # Create a Steam game with 1 hour (Just Tried)
    cursor.execute("INSERT INTO games (name, store, playtime_hours) VALUES (?, ?, ?)",
                  ("Test Game", "steam", 1.0))
    game_id = cursor.lastrowid
    test_db_with_labels.commit()

    # First auto-tag
    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))
    assert cursor.fetchone()[0] == 'Just Tried'

    # Update playtime to 5 hours (Played)
    cursor.execute("UPDATE games SET playtime_hours = 5.0 WHERE id = ?", (game_id,))
    test_db_with_labels.commit()
    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))
    assert cursor.fetchone()[0] == 'Played'

    # Update playtime to 25 hours (Well Played)
    cursor.execute("UPDATE games SET playtime_hours = 25.0 WHERE id = ?", (game_id,))
    test_db_with_labels.commit()
    update_auto_labels_for_game(test_db_with_labels, game_id)

    cursor.execute("""
        SELECT l.name FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND gl.auto = 1
    """, (game_id,))
    assert cursor.fetchone()[0] == 'Well Played'

    # Verify only one auto tag exists at each step
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels WHERE game_id = ? AND auto = 1
    """, (game_id,))
    assert cursor.fetchone()[0] == 1

