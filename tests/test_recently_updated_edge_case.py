"""Test Recently Updated filter edge cases (task 10.3)."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
from datetime import datetime, timedelta
from web.utils.filters import PREDEFINED_QUERIES


@pytest.fixture
def test_db():
    """Create a test database with sample games."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create games table
    cursor.execute("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            store TEXT,
            last_modified TIMESTAMP,
            total_rating REAL,
            added_at TIMESTAMP
        )
    """)
    
    # Insert some games
    now = datetime.now()
    old_date = now - timedelta(days=60)
    recent_date = now - timedelta(days=15)
    
    cursor.executemany("""
        INSERT INTO games (name, store, last_modified, total_rating, added_at)
        VALUES (?, ?, ?, ?, ?)
    """, [
        ("Old Game", "steam", old_date.isoformat(), 85.0, old_date.isoformat()),
        ("Recently Modified Game", "epic", recent_date.isoformat(), 80.0, old_date.isoformat()),
        ("No Modification Date", "gog", None, 75.0, old_date.isoformat()),
    ])
    
    conn.commit()
    yield conn
    conn.close()


def test_recently_updated_query_condition():
    """Verify the SQL condition for Recently Updated filter."""
    query = PREDEFINED_QUERIES.get("recently-updated")
    
    assert query is not None
    # The filter uses last_modified field which is updated for all stores
    assert "last_modified" in query
    assert "30 days" in query


def test_recently_updated_filter_logic(test_db):
    """Test Recently Updated filter with various modification dates."""
    cursor = test_db.cursor()
    
    # Test the SQL condition directly
    query_condition = PREDEFINED_QUERIES["recently-updated"]
    sql = f"""
        SELECT name FROM games
        WHERE {query_condition}
    """
    
    cursor.execute(sql)
    results = cursor.fetchall()
    
    # Should return only the recently modified game
    assert len(results) == 1
    assert results[0][0] == "Recently Modified Game"


def test_recently_updated_with_null_dates(test_db):
    """Test that NULL last_modified dates don't cause errors."""
    cursor = test_db.cursor()
    
    query_condition = PREDEFINED_QUERIES["recently-updated"]
    sql = f"""
        SELECT name FROM games
        WHERE {query_condition}
    """
    
    # Should execute without error even with NULL values
    cursor.execute(sql)
    results = cursor.fetchall()
    
    # NULL dates are excluded (not recent)
    assert "No Modification Date" not in [r[0] for r in results]


def test_recently_updated_works_all_stores(test_db):
    """Test that Recently Updated filter works across all stores."""
    # The last_modified field is populated for all stores when games are refreshed
    # Unlike game_update_at which was Epic-specific
    
    cursor = test_db.cursor()
    
    # Insert recent games from different stores
    now = datetime.now()
    recent = now - timedelta(days=5)
    
    cursor.executemany("""
        INSERT INTO games (name, store, last_modified, total_rating, added_at)
        VALUES (?, ?, ?, ?, ?)
    """, [
        ("Recent Steam", "steam", recent.isoformat(), 85.0, recent.isoformat()),
        ("Recent Epic", "epic", recent.isoformat(), 80.0, recent.isoformat()),
        ("Recent GOG", "gog", recent.isoformat(), 75.0, recent.isoformat()),
    ])
    test_db.commit()
    
    # Query with recently-updated filter
    query_condition = PREDEFINED_QUERIES["recently-updated"]
    sql = f"""
        SELECT name, store FROM games
        WHERE {query_condition}
        ORDER BY name
    """
    
    cursor.execute(sql)
    results = cursor.fetchall()
    
    # Should include games from all stores
    names = [r[0] for r in results]
    assert "Recent Steam" in names
    assert "Recent Epic" in names
    assert "Recent GOG" in names
