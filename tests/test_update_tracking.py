"""Tests for update tracking functionality."""
import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from web.services.update_tracker import UpdateTracker, SteamUpdateTracker


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create games table
    cursor.execute("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            store TEXT NOT NULL,
            store_id TEXT,
            last_modified TIMESTAMP,
            development_status TEXT
        )
    """)
    
    # Create game_depot_updates table
    cursor.execute("""
        CREATE TABLE game_depot_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            depot_id TEXT,
            manifest_id TEXT,
            update_timestamp TIMESTAMP,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    os.unlink(db_path)


def test_steam_metadata_fetch():
    """Test fetching Steam game metadata (integration test - requires internet)."""
    tracker = SteamUpdateTracker()
    
    # Test with a known game (Dota 2 - appid 570)
    metadata = tracker.fetch_metadata("570")
    
    # Should return metadata dict or None (API might fail)
    if metadata:
        assert 'development_status' in metadata
        assert metadata['development_status'] in ['early_access', 'released']


def test_update_detection_version_change(temp_db):
    """Test detection of version updates (last_modified change)."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert a test game with old last_modified
    old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
    cursor.execute("""
        INSERT INTO games (name, store, store_id, last_modified, development_status)
        VALUES (?, ?, ?, ?, ?)
    """, ("Test Game", "steam", "12345", old_timestamp, "released"))
    
    game_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Create tracker
    tracker = UpdateTracker(temp_db)
    
    # Mock the fetch_metadata to return new timestamp
    new_timestamp = datetime.now().isoformat()
    
    class MockSteamTracker:
        def fetch_metadata(self, appid):
            return {
                'last_modified': new_timestamp,
                'development_status': 'released'
            }
    
    tracker.steam_tracker = MockSteamTracker()
    
    # Check for updates
    result = tracker.check_updates_for_game(game_id, 'steam', '12345')
    
    # Should detect update
    assert result is True
    
    # Verify update was recorded
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT last_modified FROM games WHERE id = ?", (game_id,))
    updated_timestamp = cursor.fetchone()[0]
    assert updated_timestamp == new_timestamp
    
    cursor.execute("SELECT COUNT(*) FROM game_depot_updates WHERE game_id = ?", (game_id,))
    update_count = cursor.fetchone()[0]
    assert update_count == 1
    
    conn.close()


def test_update_detection_ea_release(temp_db):
    """Test detection of Early Access → Released transition."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert a test game in Early Access
    cursor.execute("""
        INSERT INTO games (name, store, store_id, development_status)
        VALUES (?, ?, ?, ?)
    """, ("EA Game", "steam", "54321", "early_access"))
    
    game_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Create tracker
    tracker = UpdateTracker(temp_db)
    
    # Mock the fetch_metadata to return released status
    class MockSteamTracker:
        def fetch_metadata(self, appid):
            return {
                'last_modified': None,
                'development_status': 'released'
            }
    
    tracker.steam_tracker = MockSteamTracker()
    
    # Check for updates
    result = tracker.check_updates_for_game(game_id, 'steam', '54321')
    
    # Should detect update
    assert result is True
    
    # Verify status was updated
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT development_status FROM games WHERE id = ?", (game_id,))
    new_status = cursor.fetchone()[0]
    assert new_status == 'released'
    
    cursor.execute("SELECT COUNT(*) FROM game_depot_updates WHERE game_id = ? AND manifest_id = 'ea_release'", (game_id,))
    update_count = cursor.fetchone()[0]
    assert update_count == 1
    
    conn.close()


def test_no_update_detected(temp_db):
    """Test that no update is detected when metadata hasn't changed."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Insert a test game
    timestamp = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO games (name, store, store_id, last_modified, development_status)
        VALUES (?, ?, ?, ?, ?)
    """, ("Stable Game", "steam", "99999", timestamp, "released"))
    
    game_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Create tracker
    tracker = UpdateTracker(temp_db)
    
    # Mock the fetch_metadata to return same data
    class MockSteamTracker:
        def fetch_metadata(self, appid):
            return {
                'last_modified': timestamp,
                'development_status': 'released'
            }
    
    tracker.steam_tracker = MockSteamTracker()
    
    # Check for updates
    result = tracker.check_updates_for_game(game_id, 'steam', '99999')
    
    # Should NOT detect update
    assert result is False
    
    # Verify no update record was created
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM game_depot_updates WHERE game_id = ?", (game_id,))
    update_count = cursor.fetchone()[0]
    assert update_count == 0
    
    conn.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
