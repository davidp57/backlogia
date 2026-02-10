"""
Integration tests for metadata API endpoints

Tests priority, personal ratings, manual playtime tags, and bulk actions.
"""

import sys
from pathlib import Path

# Add parent directory to path to import web modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
from fastapi.testclient import TestClient
from web.main import app
from web.dependencies import get_db


@pytest.fixture
def test_db():
    """Create a test database with necessary tables"""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create games table with metadata columns
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

    # Insert test games
    cursor.execute("""
        INSERT INTO games (id, name, store, playtime_hours)
        VALUES
            (1, 'Test Game 1', 'steam', 5.0),
            (2, 'Test Game 2', 'steam', 25.0),
            (3, 'Test Game 3', 'gog', 0.5),
            (4, 'Test Game 4', 'epic', NULL),
            (5, 'Test Game 5', 'steam', 100.0)
    """)

    # Insert system labels
    system_labels = [
        ('Never Launched', 'system_tag', ':video_game:', '#64748b', 1),
        ('Just Tried', 'system_tag', ':eyes:', '#f59e0b', 1),
        ('Played', 'system_tag', ':dart:', '#3b82f6', 1),
        ('Well Played', 'system_tag', ':star:', '#8b5cf6', 1),
        ('Heavily Played', 'system_tag', ':trophy:', '#10b981', 1),
    ]
    cursor.executemany("""
        INSERT INTO labels (name, type, icon, color, system)
        VALUES (?, ?, ?, ?, ?)
    """, system_labels)

    # Insert a user collection
    cursor.execute("""
        INSERT INTO labels (name, type, icon, color, system)
        VALUES ('Favorites', 'collection', ':star:', '#fbbf24', 0)
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def client(test_db):
    """Create test client with mocked database dependency"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Don't close as test_db fixture handles cleanup

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


# ============================================================================
# Priority Endpoints Tests
# ============================================================================

def test_set_game_priority_high(client):
    """Test setting priority to high"""
    response = client.post("/api/game/1/priority", json={"priority": "high"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["priority"] == "high"


def test_set_game_priority_medium(client):
    """Test setting priority to medium"""
    response = client.post("/api/game/2/priority", json={"priority": "medium"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["priority"] == "medium"


def test_set_game_priority_low(client):
    """Test setting priority to low"""
    response = client.post("/api/game/3/priority", json={"priority": "low"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["priority"] == "low"


def test_set_game_priority_null(client):
    """Test clearing priority (setting to null)"""
    # Set a priority first
    client.post("/api/game/1/priority", json={"priority": "high"})
    
    # Clear it
    response = client.post("/api/game/1/priority", json={"priority": None})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["priority"] is None


def test_set_game_priority_invalid_value(client):
    """Test invalid priority value returns 400"""
    response = client.post("/api/game/1/priority", json={"priority": "invalid"})
    assert response.status_code == 400
    assert "Priority must be" in response.json()["detail"]


def test_set_game_priority_nonexistent_game(client):
    """Test setting priority for non-existent game returns 404"""
    response = client.post("/api/game/9999/priority", json={"priority": "high"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Personal Rating Endpoints Tests
# ============================================================================

def test_set_personal_rating_valid(client):
    """Test setting personal rating with valid values (1-10)"""
    for rating in [1, 5, 8, 10]:
        response = client.post("/api/game/1/personal-rating", json={"rating": rating})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rating"] == rating


def test_set_personal_rating_zero_removes_rating(client):
    """Test rating=0 removes the rating (sets to NULL)"""
    # Set a rating first
    client.post("/api/game/1/personal-rating", json={"rating": 8})
    
    # Remove it with 0
    response = client.post("/api/game/1/personal-rating", json={"rating": 0})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["rating"] == 0


def test_set_personal_rating_out_of_range_high(client):
    """Test rating > 10 returns 400"""
    response = client.post("/api/game/1/personal-rating", json={"rating": 11})
    assert response.status_code == 400
    assert "between 0 and 10" in response.json()["detail"]


def test_set_personal_rating_out_of_range_low(client):
    """Test rating < 0 returns 400"""
    response = client.post("/api/game/1/personal-rating", json={"rating": -1})
    assert response.status_code == 400
    assert "between 0 and 10" in response.json()["detail"]


def test_set_personal_rating_nonexistent_game(client):
    """Test setting rating for non-existent game returns 404"""
    response = client.post("/api/game/9999/personal-rating", json={"rating": 5})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Manual Playtime Tag Endpoints Tests
# ============================================================================

def test_set_manual_playtime_tag(client, test_db):
    """Test setting manual playtime tag"""
    response = client.post("/api/game/4/manual-playtime-tag", json={"label_name": "Well Played"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Well Played" in data["message"]

    # Verify tag was added with auto=0
    cursor = test_db.cursor()
    cursor.execute("""
        SELECT auto FROM game_labels gl
        JOIN labels l ON l.id = gl.label_id
        WHERE gl.game_id = 4 AND l.name = 'Well Played'
    """)
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == 0  # auto=0 (manual tag)


def test_set_manual_playtime_tag_replaces_existing(client, test_db):
    """Test manual tag replaces any existing playtime tags"""
    # Set first tag
    client.post("/api/game/4/manual-playtime-tag", json={"label_name": "Played"})
    
    # Set second tag (should replace first)
    response = client.post("/api/game/4/manual-playtime-tag", json={"label_name": "Well Played"})
    assert response.status_code == 200

    # Verify only one tag exists
    cursor = test_db.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels gl
        JOIN labels l ON l.id = gl.label_id
        WHERE gl.game_id = 4 AND l.system = 1 AND l.type = 'system_tag'
    """)
    count = cursor.fetchone()[0]
    assert count == 1


def test_remove_manual_playtime_tag(client, test_db):
    """Test removing playtime tag by passing null"""
    # Set a tag first
    client.post("/api/game/4/manual-playtime-tag", json={"label_name": "Played"})
    
    # Remove it
    response = client.post("/api/game/4/manual-playtime-tag", json={"label_name": None})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "removed" in data["message"].lower()

    # Verify tag was removed
    cursor = test_db.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM game_labels gl
        JOIN labels l ON l.id = gl.label_id
        WHERE gl.game_id = 4 AND l.system = 1
    """)
    count = cursor.fetchone()[0]
    assert count == 0


def test_set_manual_playtime_tag_invalid_label(client):
    """Test setting non-existent label returns 404"""
    response = client.post("/api/game/1/manual-playtime-tag", json={"label_name": "Invalid Label"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_set_manual_playtime_tag_nonexistent_game(client):
    """Test setting tag for non-existent game returns 404"""
    response = client.post("/api/game/9999/manual-playtime-tag", json={"label_name": "Played"})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# Bulk Priority Tests
# ============================================================================

def test_bulk_set_priority(client, test_db):
    """Test setting priority for multiple games"""
    response = client.post("/api/games/bulk/set-priority", json={
        "game_ids": [1, 2, 3],
        "priority": "high"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] == 3

    # Verify all games have high priority
    cursor = test_db.cursor()
    cursor.execute("SELECT priority FROM games WHERE id IN (1, 2, 3)")
    priorities = [row[0] for row in cursor.fetchall()]
    assert all(p == "high" for p in priorities)


def test_bulk_set_priority_empty_list(client):
    """Test bulk priority with empty game_ids returns 400"""
    response = client.post("/api/games/bulk/set-priority", json={
        "game_ids": [],
        "priority": "high"
    })
    assert response.status_code == 400
    assert "No games selected" in response.json()["detail"]


def test_bulk_set_priority_invalid_value(client):
    """Test bulk priority with invalid value returns 400"""
    response = client.post("/api/games/bulk/set-priority", json={
        "game_ids": [1, 2],
        "priority": "invalid"
    })
    assert response.status_code == 400
    assert "Priority must be" in response.json()["detail"]


# ============================================================================
# Bulk Personal Rating Tests
# ============================================================================

def test_bulk_set_personal_rating(client, test_db):
    """Test setting personal rating for multiple games"""
    response = client.post("/api/games/bulk/set-personal-rating", json={
        "game_ids": [1, 2, 3],
        "rating": 8
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] == 3

    # Verify all games have rating=8
    cursor = test_db.cursor()
    cursor.execute("SELECT personal_rating FROM games WHERE id IN (1, 2, 3)")
    ratings = [row[0] for row in cursor.fetchall()]
    assert all(r == 8 for r in ratings)


def test_bulk_set_personal_rating_zero_removes(client, test_db):
    """Test bulk rating=0 removes ratings for all selected games"""
    # Set ratings first
    client.post("/api/games/bulk/set-personal-rating", json={
        "game_ids": [1, 2],
        "rating": 7
    })

    # Remove with rating=0
    response = client.post("/api/games/bulk/set-personal-rating", json={
        "game_ids": [1, 2],
        "rating": 0
    })
    assert response.status_code == 200
    assert response.json()["updated"] == 2

    # Verify ratings are NULL
    cursor = test_db.cursor()
    cursor.execute("SELECT personal_rating FROM games WHERE id IN (1, 2)")
    ratings = [row[0] for row in cursor.fetchall()]
    assert all(r is None for r in ratings)


def test_bulk_set_personal_rating_empty_list(client):
    """Test bulk rating with empty game_ids returns 400"""
    response = client.post("/api/games/bulk/set-personal-rating", json={
        "game_ids": [],
        "rating": 5
    })
    assert response.status_code == 400
    assert "No games selected" in response.json()["detail"]


def test_bulk_set_personal_rating_out_of_range(client):
    """Test bulk rating with out-of-range value returns 400"""
    response = client.post("/api/games/bulk/set-personal-rating", json={
        "game_ids": [1, 2],
        "rating": 15
    })
    assert response.status_code == 400
    assert "between 0 and 10" in response.json()["detail"]


# ============================================================================
# Bulk Hide Tests
# ============================================================================

def test_bulk_hide_games(client, test_db):
    """Test hiding multiple games"""
    response = client.post("/api/games/bulk/hide", json={"game_ids": [1, 2, 3]})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] == 3

    # Verify all games are hidden
    cursor = test_db.cursor()
    cursor.execute("SELECT hidden FROM games WHERE id IN (1, 2, 3)")
    hidden_flags = [row[0] for row in cursor.fetchall()]
    assert all(h == 1 for h in hidden_flags)


def test_bulk_hide_empty_list(client):
    """Test bulk hide with empty game_ids returns 400"""
    response = client.post("/api/games/bulk/hide", json={"game_ids": []})
    assert response.status_code == 400
    assert "No games selected" in response.json()["detail"]


# ============================================================================
# Bulk NSFW Tests
# ============================================================================

def test_bulk_nsfw_games(client, test_db):
    """Test marking multiple games as NSFW"""
    response = client.post("/api/games/bulk/nsfw", json={"game_ids": [1, 2, 3]})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["updated"] == 3

    # Verify all games are marked NSFW
    cursor = test_db.cursor()
    cursor.execute("SELECT nsfw FROM games WHERE id IN (1, 2, 3)")
    nsfw_flags = [row[0] for row in cursor.fetchall()]
    assert all(n == 1 for n in nsfw_flags)


def test_bulk_nsfw_empty_list(client):
    """Test bulk NSFW with empty game_ids returns 400"""
    response = client.post("/api/games/bulk/nsfw", json={"game_ids": []})
    assert response.status_code == 400
    assert "No games selected" in response.json()["detail"]


# ============================================================================
# Bulk Delete Tests
# ============================================================================

def test_bulk_delete_games(client, test_db):
    """Test deleting multiple games"""
    response = client.post("/api/games/bulk/delete", json={"game_ids": [1, 2, 3]})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted"] == 3

    # Verify games are deleted
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM games WHERE id IN (1, 2, 3)")
    count = cursor.fetchone()[0]
    assert count == 0


def test_bulk_delete_removes_labels_association(client, test_db):
    """Test bulk delete removes game_labels associations"""
    # Add game to collection
    cursor = test_db.cursor()
    cursor.execute("INSERT INTO game_labels (label_id, game_id) VALUES (6, 1)")
    test_db.commit()

    # Delete game
    response = client.post("/api/games/bulk/delete", json={"game_ids": [1]})
    assert response.status_code == 200

    # Verify game_labels entry removed
    cursor.execute("SELECT COUNT(*) FROM game_labels WHERE game_id = 1")
    count = cursor.fetchone()[0]
    assert count == 0


def test_bulk_delete_empty_list(client):
    """Test bulk delete with empty game_ids returns 400"""
    response = client.post("/api/games/bulk/delete", json={"game_ids": []})
    assert response.status_code == 400
    assert "No games selected" in response.json()["detail"]


# ============================================================================
# Bulk Add to Collection Tests
# ============================================================================

def test_bulk_add_to_collection(client, test_db):
    """Test adding multiple games to a collection"""
    response = client.post("/api/games/bulk/add-to-collection", json={
        "game_ids": [1, 2, 3],
        "collection_id": 6  # Favorites collection
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["added"] >= 3  # May be less if duplicates existed

    # Verify games are in collection
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM game_labels WHERE label_id = 6 AND game_id IN (1, 2, 3)")
    count = cursor.fetchone()[0]
    assert count == 3


def test_bulk_add_to_collection_nonexistent_label(client):
    """Test adding to non-existent collection returns 404"""
    response = client.post("/api/games/bulk/add-to-collection", json={
        "game_ids": [1, 2],
        "collection_id": 9999
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_bulk_add_to_collection_empty_list(client):
    """Test bulk add with empty game_ids returns 400"""
    response = client.post("/api/games/bulk/add-to-collection", json={
        "game_ids": [],
        "collection_id": 6
    })
    assert response.status_code == 400
    assert "No games selected" in response.json()["detail"]


def test_bulk_add_to_collection_ignores_duplicates(client, test_db):
    """Test adding same games twice doesn't create duplicates"""
    # Add games first time
    client.post("/api/games/bulk/add-to-collection", json={
        "game_ids": [1, 2],
        "collection_id": 6
    })

    # Add same games again
    response = client.post("/api/games/bulk/add-to-collection", json={
        "game_ids": [1, 2],
        "collection_id": 6
    })
    assert response.status_code == 200
    assert response.json()["added"] == 0  # No new additions

    # Verify only one entry per game
    cursor = test_db.cursor()
    cursor.execute("SELECT COUNT(*) FROM game_labels WHERE label_id = 6 AND game_id IN (1, 2)")
    count = cursor.fetchone()[0]
    assert count == 2


# ============================================================================
# System Tags Update Tests
# ============================================================================

def test_update_system_tags_endpoint(client, test_db):
    """Test manual trigger for system tags update"""
    # Note: This test only verifies the endpoint responds successfully
    # Actual label assignment logic is tested in test_system_labels_auto_tagging.py
    response = client.post("/api/labels/update-system-tags")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "updated" in data["message"].lower()
