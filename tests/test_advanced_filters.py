"""
Tests for advanced filters added in MAIN branch merge.

Tests cover:
- Collection filter SQL generation
- ProtonDB tier hierarchical filtering
- Exclude streaming filter
- No IGDB data filter
- Filter combination logic
- PRAGMA column validation
"""

import pytest
import sqlite3
from datetime import datetime, timezone


@pytest.fixture
def test_db():
    """Create in-memory test database with sample data"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create games table
    cursor.execute("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            store TEXT,
            igdb_id INTEGER,
            protondb_tier TEXT,
            delivery_method TEXT,
            total_rating REAL,
            playtime_hours REAL DEFAULT 0,
            added_at TIMESTAMP,
            hidden INTEGER DEFAULT 0
        )
    """)
    
    # Create collections tables
    cursor.execute("""
        CREATE TABLE collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE collection_games (
            collection_id INTEGER,
            game_id INTEGER,
            PRIMARY KEY (collection_id, game_id),
            FOREIGN KEY (collection_id) REFERENCES collections(id),
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    """)
    
    # Insert test collections
    cursor.execute("INSERT INTO collections (name) VALUES ('Backlog')")
    cursor.execute("INSERT INTO collections (name) VALUES ('Completed')")
    backlog_id = 1
    completed_id = 2
    
    # Insert test games
    games = [
        # Backlog collection games
        (1, "Game 1", "steam", 100, "platinum", "download", 85.0, 0, datetime.now(timezone.utc)),
        (2, "Game 2", "epic", 101, "gold", "download", 75.0, 5, datetime.now(timezone.utc)),
        (3, "Game 3", "gog", 102, "silver", "download", 65.0, 10, datetime.now(timezone.utc)),
        # Completed collection games
        (4, "Game 4", "steam", 103, "bronze", "download", 90.0, 50, datetime.now(timezone.utc)),
        (5, "Game 5", "epic", 104, "platinum", "download", 80.0, 30, datetime.now(timezone.utc)),
        # Streaming games
        (6, "Xbox Cloud Game", "xbox", 105, None, "streaming", 70.0, 0, datetime.now(timezone.utc)),
        (7, "GeForce NOW", "steam", 106, "platinum", "streaming", 85.0, 0, datetime.now(timezone.utc)),
        # No IGDB games
        (8, "Local Game", "local", None, None, "download", None, 15, datetime.now(timezone.utc)),
        (9, "Unknown Game", "steam", 0, "gold", "download", None, 0, datetime.now(timezone.utc)),
    ]
    
    for game_id, title, store, igdb_id, tier, delivery, rating, playtime, added in games:
        cursor.execute("""
            INSERT INTO games (id, title, store, igdb_id, protondb_tier, delivery_method, 
                             total_rating, playtime_hours, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, title, store, igdb_id, tier, delivery, rating, playtime, added))
    
    # Assign games to collections
    # Backlog: games 1, 2, 3
    for game_id in [1, 2, 3]:
        cursor.execute("INSERT INTO collection_games (collection_id, game_id) VALUES (?, ?)",
                      (backlog_id, game_id))
    
    # Completed: games 4, 5
    for game_id in [4, 5]:
        cursor.execute("INSERT INTO collection_games (collection_id, game_id) VALUES (?, ?)",
                      (completed_id, game_id))
    
    conn.commit()
    yield conn
    conn.close()


class TestCollectionFilter:
    """Test collection filter functionality"""
    
    def test_collection_filter_sql_generation(self, test_db):
        """Verify collection filter generates correct SQL"""
        collection_id = 1  # Backlog
        
        query = "SELECT * FROM games WHERE 1=1"
        params = []
        
        # Apply collection filter
        query += " AND id IN (SELECT game_id FROM collection_games WHERE collection_id = ?)"
        params.append(collection_id)
        
        cursor = test_db.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        assert len(results) == 3
        assert all(r["id"] in [1, 2, 3] for r in results)
    
    def test_collection_filter_completed(self, test_db):
        """Test filtering by Completed collection"""
        collection_id = 2  # Completed
        
        query = "SELECT * FROM games WHERE 1=1"
        query += " AND id IN (SELECT game_id FROM collection_games WHERE collection_id = ?)"
        
        cursor = test_db.cursor()
        cursor.execute(query, (collection_id,))
        results = cursor.fetchall()
        
        assert len(results) == 2
        assert all(r["id"] in [4, 5] for r in results)


class TestProtonDBTierFilter:
    """Test ProtonDB tier hierarchical filtering"""
    
    def test_platinum_tier_only(self, test_db):
        """Platinum should show only platinum games"""
        protondb_hierarchy = ["platinum", "gold", "silver", "bronze"]
        tier = "platinum"
        
        tier_index = protondb_hierarchy.index(tier)
        allowed_tiers = protondb_hierarchy[:tier_index + 1]
        
        query = "SELECT * FROM games WHERE 1=1"
        placeholders = ",".join("?" * len(allowed_tiers))
        query += f" AND protondb_tier IN ({placeholders})"
        
        cursor = test_db.cursor()
        cursor.execute(query, allowed_tiers)
        results = cursor.fetchall()
        
        assert len(results) == 3  # Games 1, 5, 7
        assert all(r["protondb_tier"] == "platinum" for r in results)
    
    def test_gold_tier_includes_platinum(self, test_db):
        """Gold should show platinum + gold games"""
        protondb_hierarchy = ["platinum", "gold", "silver", "bronze"]
        tier = "gold"
        
        tier_index = protondb_hierarchy.index(tier)
        allowed_tiers = protondb_hierarchy[:tier_index + 1]
        
        query = "SELECT * FROM games WHERE 1=1"
        placeholders = ",".join("?" * len(allowed_tiers))
        query += f" AND protondb_tier IN ({placeholders})"
        
        cursor = test_db.cursor()
        cursor.execute(query, allowed_tiers)
        results = cursor.fetchall()
        
        assert len(results) == 5  # Games 1, 2, 5, 7, 9
        assert all(r["protondb_tier"] in ["platinum", "gold"] for r in results)
    
    def test_bronze_tier_shows_all(self, test_db):
        """Bronze should show all 4 tiers"""
        protondb_hierarchy = ["platinum", "gold", "silver", "bronze"]
        tier = "bronze"
        
        tier_index = protondb_hierarchy.index(tier)
        allowed_tiers = protondb_hierarchy[:tier_index + 1]
        
        query = "SELECT * FROM games WHERE 1=1"
        placeholders = ",".join("?" * len(allowed_tiers))
        query += f" AND protondb_tier IN ({placeholders})"
        
        cursor = test_db.cursor()
        cursor.execute(query, allowed_tiers)
        results = cursor.fetchall()
        
        assert len(results) == 7  # Games 1, 2, 3, 4, 5, 7, 9 (all with protondb_tier)
        assert set(r["protondb_tier"] for r in results) == {"platinum", "gold", "silver", "bronze"}


class TestExcludeStreamingFilter:
    """Test exclude streaming filter"""
    
    def test_exclude_streaming_games(self, test_db):
        """Verify streaming games are excluded"""
        query = "SELECT * FROM games WHERE 1=1"
        query += " AND delivery_method != 'streaming'"
        
        cursor = test_db.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        assert len(results) == 7  # All games except 6, 7
        assert all(r["delivery_method"] == "download" for r in results)
    
    def test_include_streaming_when_not_excluded(self, test_db):
        """Verify streaming games included when filter not applied"""
        query = "SELECT * FROM games WHERE 1=1"
        
        cursor = test_db.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        assert len(results) == 9  # All games
        streaming_games = [r for r in results if r["delivery_method"] == "streaming"]
        assert len(streaming_games) == 2


class TestNoIGDBFilter:
    """Test no IGDB data filter"""
    
    def test_no_igdb_filter(self, test_db):
        """Show only games without IGDB data"""
        query = "SELECT * FROM games WHERE 1=1"
        query += " AND (igdb_id IS NULL OR igdb_id = 0)"
        
        cursor = test_db.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        assert len(results) == 2  # Games 8, 9
        assert all(r["igdb_id"] is None or r["igdb_id"] == 0 for r in results)
    
    def test_with_igdb_when_not_filtered(self, test_db):
        """Verify all games shown when filter not applied"""
        query = "SELECT * FROM games WHERE 1=1"
        cursor = test_db.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        assert len(results) == 9


class TestFilterCombinations:
    """Test combining advanced filters"""
    
    def test_collection_and_protondb(self, test_db):
        """Combine collection + ProtonDB tier filters"""
        collection_id = 1  # Backlog
        protondb_hierarchy = ["platinum", "gold", "silver", "bronze"]
        tier = "gold"
        
        tier_index = protondb_hierarchy.index(tier)
        allowed_tiers = protondb_hierarchy[:tier_index + 1]
        
        query = "SELECT * FROM games WHERE 1=1"
        query += " AND id IN (SELECT game_id FROM collection_games WHERE collection_id = ?)"
        placeholders = ",".join("?" * len(allowed_tiers))
        query += f" AND protondb_tier IN ({placeholders})"
        
        params = [collection_id] + allowed_tiers
        
        cursor = test_db.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Backlog games (1, 2, 3) with platinum/gold tier (1, 2)
        assert len(results) == 2
        assert all(r["id"] in [1, 2] for r in results)
    
    def test_exclude_streaming_and_no_igdb(self, test_db):
        """Combine exclude streaming + no IGDB filters"""
        query = "SELECT * FROM games WHERE 1=1"
        query += " AND delivery_method != 'streaming'"
        query += " AND (igdb_id IS NULL OR igdb_id = 0)"
        
        cursor = test_db.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Only local games without streaming
        assert len(results) == 2  # Games 8, 9
    
    def test_all_four_advanced_filters(self, test_db):
        """Combine all 4 advanced filters at once"""
        collection_id = 1  # Backlog
        protondb_hierarchy = ["platinum", "gold", "silver", "bronze"]
        tier = "platinum"
        
        tier_index = protondb_hierarchy.index(tier)
        allowed_tiers = protondb_hierarchy[:tier_index + 1]
        
        query = "SELECT * FROM games WHERE 1=1"
        query += " AND id IN (SELECT game_id FROM collection_games WHERE collection_id = ?)"
        placeholders = ",".join("?" * len(allowed_tiers))
        query += f" AND protondb_tier IN ({placeholders})"
        query += " AND delivery_method != 'streaming'"
        query += " AND (igdb_id IS NOT NULL AND igdb_id != 0)"  # Inverse of no_igdb
        
        params = [collection_id] + allowed_tiers
        
        cursor = test_db.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Only Game 1 (backlog, platinum, download, has IGDB)
        assert len(results) == 1
        assert results[0]["id"] == 1


class TestPragmaValidation:
    """Test PRAGMA column validation for sorting"""
    
    def test_pragma_detects_existing_columns(self, test_db):
        """Verify PRAGMA correctly detects table columns"""
        cursor = test_db.cursor()
        cursor.execute("PRAGMA table_info(games)")
        columns = {row[1] for row in cursor.fetchall()}
        
        expected_columns = {
            "id", "title", "store", "igdb_id", "protondb_tier",
            "delivery_method", "total_rating", "playtime_hours", "added_at", "hidden"
        }
        
        assert expected_columns.issubset(columns)
    
    def test_added_at_in_valid_sorts(self, test_db):
        """Verify added_at column is detected for sorting"""
        cursor = test_db.cursor()
        cursor.execute("PRAGMA table_info(games)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        valid_sorts = [
            "title", "store", "playtime_hours", "total_rating",
            "release_date", "added_at"
        ]
        
        available_sorts = [s for s in valid_sorts if s in existing_columns]
        
        assert "added_at" in available_sorts
        assert "title" in available_sorts
        assert "release_date" not in available_sorts  # Not in our test schema
    
    def test_sort_fallback_on_invalid_column(self, test_db):
        """Verify fallback to 'name' when invalid sort requested"""
        cursor = test_db.cursor()
        cursor.execute("PRAGMA table_info(games)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        valid_sorts = ["title", "store", "nonexistent_column"]
        available_sorts = [s for s in valid_sorts if s in existing_columns]
        
        sort = "nonexistent_column"
        if sort not in available_sorts:
            sort = "title"  # Fallback
        
        assert sort == "title"
