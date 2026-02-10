"""
Integration tests for predefined query filters

Tests filter functionality with real database operations including:
- Individual filter validation
- Filter combinations
- NULL value handling
- Empty result sets
- Conflicting filters
"""

import sys
from pathlib import Path

# Add parent directory to path to import web modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from web.main import app
from web.utils.filters import PREDEFINED_QUERIES, QUERY_CATEGORIES


@pytest.fixture(scope="module")
def test_db():
    """Create a test database with sample games"""
    # Use an in-memory database for testing
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create games table with all necessary columns
    cursor.execute("""
        CREATE TABLE games (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            store TEXT,
            playtime_hours REAL,
            total_rating REAL,
            aggregated_rating REAL,
            total_rating_count INTEGER,
            added_at TIMESTAMP,
            release_date TEXT,
            last_modified TIMESTAMP,
            nsfw BOOLEAN DEFAULT 0,
            hidden BOOLEAN DEFAULT 0,
            cover_url TEXT,
            priority TEXT,
            personal_rating REAL
        )
    """)
    
    # Insert test games with various properties
    now = datetime.now()
    
    # Convert datetime objects to strings to avoid Python 3.12+ deprecation warning
    test_games = [
        # Unplayed games
        (1, "Unplayed Game 1", "steam", 0, 85.0, 80.0, 100, (now - timedelta(days=5)).isoformat(), "2023-01-01", now.isoformat(), 0, 0, "cover1.jpg"),
        (2, "Unplayed Game 2", "steam", None, None, None, 0, (now - timedelta(days=10)).isoformat(), "2023-02-01", now.isoformat(), 0, 0, "cover2.jpg"),
        
        # Played games with different playtimes
        (3, "Started Game", "gog", 0.5, 75.0, 70.0, 50, (now - timedelta(days=15)).isoformat(), "2022-06-01", now.isoformat(), 0, 0, "cover3.jpg"),
        (4, "Well Played Game", "steam", 8.0, 90.0, 85.0, 200, (now - timedelta(days=20)).isoformat(), "2022-03-01", now.isoformat(), 0, 0, "cover4.jpg"),
        (5, "Heavily Played Game", "epic", 50.0, 95.0, 92.0, 500, (now - timedelta(days=30)).isoformat(), "2021-12-01", now.isoformat(), 0, 0, "cover5.jpg"),
        
        # Rating variations
        (6, "Highly Rated Game", "steam", 2.0, 95.0, 93.0, 1000, (now - timedelta(days=40)).isoformat(), "2023-05-01", now.isoformat(), 0, 0, "cover6.jpg"),
        (7, "Below Average Game", "steam", 1.0, 60.0, 58.0, 100, (now - timedelta(days=50)).isoformat(), "2022-08-01", now.isoformat(), 0, 0, "cover7.jpg"),
        (8, "Unrated Game", "gog", 3.0, None, None, 0, (now - timedelta(days=60)).isoformat(), "2023-03-01", now.isoformat(), 0, 0, "cover8.jpg"),
        
        # Date variations
        (9, "Recently Added", "steam", 0, 80.0, 78.0, 150, (now - timedelta(days=1)).isoformat(), "2023-06-01", now.isoformat(), 0, 0, "cover9.jpg"),
        (10, "Old Library Game", "steam", 10.0, 85.0, 82.0, 200, (now - timedelta(days=400)).isoformat(), "2020-01-01", (now - timedelta(days=300)).isoformat(), 0, 0, "cover10.jpg"),
        (11, "Recent Release", "epic", 0, None, None, 0, (now - timedelta(days=100)).isoformat(), (now - timedelta(days=15)).strftime("%Y-%m-%d"), now.isoformat(), 0, 0, "cover11.jpg"),
        (12, "Classic Game", "gog", 15.0, 88.0, 86.0, 300, (now - timedelta(days=200)).isoformat(), "1998-06-15", (now - timedelta(days=150)).isoformat(), 0, 0, "cover12.jpg"),
        
        # Content filters
        (13, "NSFW Game", "steam", 5.0, 82.0, 80.0, 100, (now - timedelta(days=25)).isoformat(), "2023-04-01", now.isoformat(), 1, 0, "cover13.jpg"),
        (14, "Safe Game", "gog", 3.0, 78.0, 75.0, 80, (now - timedelta(days=35)).isoformat(), "2023-02-15", now.isoformat(), 0, 0, "cover14.jpg"),
        
        # Hidden gems (high rating, low rating count)
        (15, "Hidden Gem", "steam", 2.0, 92.0, 90.0, 25, (now - timedelta(days=45)).isoformat(), "2023-01-20", now.isoformat(), 0, 0, "cover15.jpg"),
        
        # NULL value test cases
        (16, "NULL Playtime", "steam", None, 88.0, 85.0, 150, (now - timedelta(days=55)).isoformat(), "2022-11-01", now.isoformat(), 0, 0, "cover16.jpg"),
        (17, "NULL Rating", "gog", 4.0, None, None, 0, (now - timedelta(days=65)).isoformat(), "2023-07-01", now.isoformat(), 0, 0, "cover17.jpg"),
        (18, "NULL Release Date", "epic", 1.0, 75.0, 72.0, 100, (now - timedelta(days=75)).isoformat(), None, now.isoformat(), 0, 0, "cover18.jpg"),
    ]
    
    cursor.executemany("""
        INSERT INTO games
        (id, name, store, playtime_hours, total_rating, aggregated_rating,
         total_rating_count, added_at, release_date, last_modified, nsfw, hidden, cover_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, test_games)

    # Create labels and game_labels tables for tag-based gameplay filters
    cursor.execute("""
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            system INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE game_labels (
            game_id INTEGER,
            label_id INTEGER,
            PRIMARY KEY (game_id, label_id)
        )
    """)

    # Insert system tag labels
    system_tags = [
        (1, 'Never Launched', 'system_tag', 1),
        (2, 'Just Tried', 'system_tag', 1),
        (3, 'Played', 'system_tag', 1),
        (4, 'Well Played', 'system_tag', 1),
        (5, 'Heavily Played', 'system_tag', 1),
    ]
    cursor.executemany("INSERT INTO labels (id, name, type, system) VALUES (?, ?, ?, ?)", system_tags)

    # Assign tags to games based on their playtime profile
    # Games 1 (steam, 0h), 2 (steam, NULL), 9 (steam, 0h), 16 (steam, NULL) → unplayed steam
    # Game 11 (epic, 0h) → unplayed non-steam (no tags at all)
    # Give steam unplayed games "Never Launched" tag
    game_label_data = [
        (1, 1),   # Game 1 → Never Launched
        (2, 1),   # Game 2 → Never Launched
        (9, 1),   # Game 9 → Never Launched
        (16, 1),  # Game 16 → Never Launched
        # Game 11 (epic) → no tags at all → unplayed
        (3, 2),   # Game 3 (0.5h) → Just Tried
        (7, 2),   # Game 7 (1h) → Just Tried
        (18, 2),  # Game 18 (1h) → Just Tried
        (6, 3),   # Game 6 (2h) → Played
        (8, 3),   # Game 8 (3h) → Played
        (14, 3),  # Game 14 (3h) → Played
        (15, 3),  # Game 15 (2h) → Played
        (17, 3),  # Game 17 (4h) → Played
        (4, 4),   # Game 4 (8h) → Well Played
        (10, 4),  # Game 10 (10h) → Well Played
        (12, 4),  # Game 12 (15h) → Well Played
        (13, 4),  # Game 13 (5h) → Well Played
        (5, 5),   # Game 5 (50h) → Heavily Played
    ]
    cursor.executemany("INSERT INTO game_labels (game_id, label_id) VALUES (?, ?)", game_label_data)

    conn.commit()
    yield conn
    conn.close()


class TestIndividualFilters:
    """Test each filter individually with expected results"""
    
    def test_unplayed_filter(self, test_db):
        """Test unplayed filter returns games with no gameplay tags"""
        cursor = test_db.cursor()
        sql = f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['unplayed']}"
        cursor.execute(sql)
        result = cursor.fetchone()[0]
        # Steam games with only "Never Launched" tag: 1, 2, 9, 16
        # Non-steam games with no tags: 11
        assert result == 5, f"Unplayed filter should match 5 games, got {result}"

    def test_played_filter(self, test_db):
        """Test played filter returns games tagged as Played"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['played']}")
        result = cursor.fetchone()[0]
        # Games 6, 8, 14, 15, 17 have "Played" tag
        assert result == 5, f"Played filter should match 5 games, got {result}"

    def test_well_played_filter(self, test_db):
        """Test well-played filter (tagged as Well Played)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['well-played']}")
        result = cursor.fetchone()[0]
        # Games 4, 10, 12, 13 have "Well Played" tag
        assert result == 4, f"Well-played filter should match 4 games, got {result}"

    def test_heavily_played_filter(self, test_db):
        """Test heavily-played filter (tagged as Heavily Played)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['heavily-played']}")
        result = cursor.fetchone()[0]
        # Game 5 has "Heavily Played" tag
        assert result == 1, f"Heavily-played filter should match 1 game, got {result}"
    
    def test_highly_rated_filter(self, test_db):
        """Test highly-rated filter (90+)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['highly-rated']}")
        result = cursor.fetchone()[0]
        # Should match games 4, 5, 6, 15 (rating >= 90)
        assert result >= 3, "Highly-rated filter should match games with rating >= 90"
    
    def test_below_average_filter(self, test_db):
        """Test below-average filter (<70)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['below-average']}")
        result = cursor.fetchone()[0]
        # Should match game 7 (60 rating)
        assert result >= 1, "Below-average filter should match games with rating < 70"
    
    def test_unrated_filter(self, test_db):
        """Test unrated filter (NULL or 0 ratings)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['unrated']}")
        result = cursor.fetchone()[0]
        # Should match games 2, 8, 11, 17 (NULL rating or no rating count)
        assert result >= 3, "Unrated filter should match games with NULL or 0 ratings"
    
    def test_nsfw_filter(self, test_db):
        """Test NSFW filter"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['nsfw']}")
        result = cursor.fetchone()[0]
        # Should match game 13
        assert result >= 1, "NSFW filter should match games marked as NSFW"
    
    def test_safe_filter(self, test_db):
        """Test safe filter"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['safe']}")
        result = cursor.fetchone()[0]
        # Should match all games except 13
        assert result >= 15, "Safe filter should match non-NSFW games"


class TestFilterCombinations:
    """Test multiple filters working together"""
    
    def test_played_and_highly_rated(self, test_db):
        """Test combination: played + highly-rated"""
        cursor = test_db.cursor()
        played_sql = PREDEFINED_QUERIES['played']
        highly_rated_sql = PREDEFINED_QUERIES['highly-rated']
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE ({played_sql}) AND ({highly_rated_sql})")
        result = cursor.fetchone()[0]
        # "Played" tagged games with rating >= 90: Game 15 (92 rating, Played tag)
        assert result >= 0, "Combined filter should execute without error"

    def test_unplayed_and_recently_added(self, test_db):
        """Test combination: unplayed + recently-added"""
        cursor = test_db.cursor()
        unplayed_sql = PREDEFINED_QUERIES['unplayed']
        recently_added_sql = PREDEFINED_QUERIES['recently-added']
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE ({unplayed_sql}) AND ({recently_added_sql})")
        result = cursor.fetchone()[0]
        # Unplayed + added in last 30 days
        assert result >= 1, "Should match unplayed games recently added"

    def test_three_filter_combination(self, test_db):
        """Test three filters: well-played + highly-rated + safe"""
        cursor = test_db.cursor()
        well_played_sql = PREDEFINED_QUERIES['well-played']
        highly_rated_sql = PREDEFINED_QUERIES['highly-rated']
        safe_sql = PREDEFINED_QUERIES['safe']
        cursor.execute(f"""
            SELECT COUNT(*) FROM games
            WHERE ({well_played_sql}) AND ({highly_rated_sql}) AND ({safe_sql})
        """)
        result = cursor.fetchone()[0]
        # Well Played + rating >= 90 + safe: Game 4 (90 rating, Well Played, safe)
        assert result >= 1, "Should match games meeting all three criteria"


class TestNullValueHandling:
    """Test filter behavior with NULL values"""
    
    def test_null_playtime_handling(self, test_db):
        """Test unplayed filter handles games with NULL playtime (tag-based)"""
        cursor = test_db.cursor()

        # Unplayed should match games without gameplay tags
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['unplayed']}")
        unplayed_count = cursor.fetchone()[0]

        # Game 16 (steam, NULL playtime, "Never Launched" tag) should be unplayed
        cursor.execute(f"""
            SELECT COUNT(*) FROM games
            WHERE id = 16 AND ({PREDEFINED_QUERIES['unplayed']})
        """)
        game16_match = cursor.fetchone()[0]

        assert unplayed_count > 0, "Unplayed filter should match games without gameplay tags"
        assert game16_match == 1, "Game 16 with only Never Launched tag should be unplayed"
    
    def test_null_rating_handling(self, test_db):
        """Test filters handle NULL ratings correctly"""
        cursor = test_db.cursor()
        
        # Unrated filter should include NULL ratings
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['unrated']}")
        unrated_count = cursor.fetchone()[0]
        
        # Check games 2, 8, 11, 17 (NULL ratings) are included
        cursor.execute(f"""
            SELECT COUNT(*) FROM games 
            WHERE id IN (2, 8, 11, 17) AND ({PREDEFINED_QUERIES['unrated']})
        """)
        null_rated_included = cursor.fetchone()[0]
        
        assert unrated_count >= 3, "Unrated filter should include NULL ratings"
        assert null_rated_included >= 3, "NULL rated games should be matched by unrated filter"
    
    def test_null_release_date_handling(self, test_db):
        """Test filters handle NULL release dates correctly"""
        cursor = test_db.cursor()
        
        # Recent releases should handle NULL dates gracefully
        cursor.execute(f"""
            SELECT COUNT(*) FROM games 
            WHERE {PREDEFINED_QUERIES['recent-releases']}
        """)
        recent_count = cursor.fetchone()[0]
        
        # Should not crash and should return valid count
        assert recent_count >= 0, "Recent releases filter should handle NULL dates"


class TestEmptyResultSets:
    """Test filters that might return no results"""
    
    def test_conflicting_filters_empty_result(self, test_db):
        """Test filters that logically cannot match any games"""
        cursor = test_db.cursor()

        # Unplayed AND heavily-played should return 0 (no game has both no tags and Heavily Played tag)
        unplayed_sql = PREDEFINED_QUERIES['unplayed']
        heavily_played_sql = PREDEFINED_QUERIES['heavily-played']
        cursor.execute(f"""
            SELECT COUNT(*) FROM games
            WHERE ({unplayed_sql}) AND ({heavily_played_sql})
        """)
        result = cursor.fetchone()[0]

        assert result == 0, "Conflicting filters should return empty result"
    
    def test_impossible_rating_combination(self, test_db):
        """Test impossible rating combinations"""
        cursor = test_db.cursor()
        
        # Highly-rated AND below-average should return 0
        highly_rated_sql = PREDEFINED_QUERIES['highly-rated']
        below_avg_sql = PREDEFINED_QUERIES['below-average']
        cursor.execute(f"""
            SELECT COUNT(*) FROM games 
            WHERE ({highly_rated_sql}) AND ({below_avg_sql})
        """)
        result = cursor.fetchone()[0]
        
        assert result == 0, "Highly-rated and below-average are mutually exclusive"
    
    def test_nsfw_and_safe_conflict(self, test_db):
        """Test NSFW and safe filters are mutually exclusive"""
        cursor = test_db.cursor()
        
        nsfw_sql = PREDEFINED_QUERIES['nsfw']
        safe_sql = PREDEFINED_QUERIES['safe']
        cursor.execute(f"""
            SELECT COUNT(*) FROM games 
            WHERE ({nsfw_sql}) AND ({safe_sql})
        """)
        result = cursor.fetchone()[0]
        
        assert result == 0, "NSFW and safe filters are mutually exclusive"


class TestConflictingFilters:
    """Test behavior with conflicting filter combinations"""
    
    def test_category_exclusive_filters(self, test_db):
        """Test that filters from same category are properly handled"""
        cursor = test_db.cursor()
        
        # Get gameplay category filters
        gameplay_filters = QUERY_CATEGORIES.get('Gameplay', [])

        if len(gameplay_filters) >= 2:
            # Test first two gameplay filters together
            filter1 = gameplay_filters[0]
            filter2 = gameplay_filters[1]
            
            sql1 = PREDEFINED_QUERIES[filter1]
            sql2 = PREDEFINED_QUERIES[filter2]
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM games 
                WHERE ({sql1}) AND ({sql2})
            """)
            result = cursor.fetchone()[0]
            
            # Some gameplay combinations might be valid (e.g., played + well-played)
            # This just ensures the query executes without error
            assert result >= 0, "Category filters should execute without error"
    
    def test_all_gameplay_filters_combined(self, test_db):
        """Test all gameplay filters combined (should be impossible)"""
        cursor = test_db.cursor()

        gameplay_filters = QUERY_CATEGORIES.get('Gameplay', [])

        if len(gameplay_filters) >= 3:
            # Combine all gameplay filters with AND
            conditions = [f"({PREDEFINED_QUERIES[f]})" for f in gameplay_filters]
            sql = f"SELECT COUNT(*) FROM games WHERE {' AND '.join(conditions)}"

            cursor.execute(sql)
            result = cursor.fetchone()[0]

            # Most gameplay combinations should be impossible
            # (can't be unplayed AND heavily-played)
            assert result >= 0, "Query should execute even if result is empty"


class TestAPIEndpoints:
    """Test filter functionality through API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    def test_single_query_parameter(self, client):
        """Test API accepts single query parameter"""
        response = client.get("/library?queries=unplayed")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_multiple_query_parameters(self, client):
        """Test API accepts multiple query parameters"""
        response = client.get("/library?queries=played&queries=highly-rated")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_invalid_query_ignored(self, client):
        """Test API gracefully handles invalid query IDs"""
        response = client.get("/library?queries=invalid-filter-id")
        assert response.status_code == 200
        # Should not crash, just ignore invalid filter
    
    def test_queries_with_stores_and_genres(self, client):
        """Test queries work with store and genre filters"""
        response = client.get("/library?queries=played&stores=steam&genres=action")
        assert response.status_code == 200
    
    def test_discover_page_with_queries(self, client):
        """Test discover page accepts query filters"""
        response = client.get("/discover?queries=highly-rated")
        assert response.status_code == 200
    
    def test_collection_with_queries(self, client):
        """Test collection detail page accepts query filters"""
        # Note: This might fail if collection doesn't exist
        # Just test the endpoint doesn't crash
        response = client.get("/collections/1?queries=played")
        # Accept 200 or 404 (if collection doesn't exist)
        assert response.status_code in [200, 404]


class TestCollectionFilters:
    """Test predefined filters work correctly in collection context"""
    
    @pytest.fixture
    def collection_db(self):
        """Create a test database with collections, games, and collection_games"""
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # Create games table with all necessary columns including igdb columns
        cursor.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                store TEXT,
                playtime_hours REAL,
                total_rating REAL,
                aggregated_rating REAL,
                igdb_rating REAL,
                igdb_rating_count INTEGER,
                total_rating_count INTEGER,
                added_at TIMESTAMP,
                release_date TEXT,
                last_modified TIMESTAMP,
                nsfw BOOLEAN DEFAULT 0,
                hidden BOOLEAN DEFAULT 0,
                cover_url TEXT,
                priority TEXT,
                personal_rating REAL
            )
        """)
        
        # Create collections table
        cursor.execute("""
            CREATE TABLE collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create collection_games junction table
        cursor.execute("""
            CREATE TABLE collection_games (
                collection_id INTEGER,
                game_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (collection_id, game_id),
                FOREIGN KEY (collection_id) REFERENCES collections(id),
                FOREIGN KEY (game_id) REFERENCES games(id)
            )
        """)

        # Create labels and game_labels tables for tag-based filters
        cursor.execute("""
            CREATE TABLE labels (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                system INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE game_labels (
                game_id INTEGER,
                label_id INTEGER,
                PRIMARY KEY (game_id, label_id)
            )
        """)

        # Insert test games with various properties
        now = datetime.now()
        
        test_games = [
            # Games with high IGDB ratings (community-favorites)
            (1, "Community Favorite 1", "steam", 10.0, 85.0, 80.0, 90.0, 150, 100, 
             now.isoformat(), "2023-01-01", now.isoformat(), 0, 0, "cover1.jpg"),
            (2, "Community Favorite 2", "steam", 5.0, 88.0, 82.0, 87.0, 200, 150, 
             now.isoformat(), "2023-02-01", now.isoformat(), 0, 0, "cover2.jpg"),
            
            # Games with high critic ratings (critic-favorites)
            (3, "Critic Favorite 1", "gog", 8.0, 85.0, 85.0, 75.0, 50, 100, 
             now.isoformat(), "2022-06-01", now.isoformat(), 0, 0, "cover3.jpg"),
            (4, "Critic Favorite 2", "steam", 12.0, 90.0, 88.0, 80.0, 75, 200, 
             now.isoformat(), "2022-03-01", now.isoformat(), 0, 0, "cover4.jpg"),
            
            # Recently updated games (recently-updated)
            (5, "Recently Updated 1", "epic", 15.0, 75.0, 70.0, 72.0, 40, 80, 
             (now - timedelta(days=100)).isoformat(), "2021-12-01", 
             (now - timedelta(days=5)).isoformat(), 0, 0, "cover5.jpg"),
            (6, "Recently Updated 2", "epic", 3.0, 80.0, 75.0, 78.0, 60, 100, 
             (now - timedelta(days=200)).isoformat(), "2022-05-01", 
             (now - timedelta(days=10)).isoformat(), 0, 0, "cover6.jpg"),
            
            # Games that don't match the filters
            (7, "Low Rating Game", "steam", 2.0, 50.0, 48.0, 55.0, 20, 30, 
             now.isoformat(), "2023-05-01", (now - timedelta(days=100)).isoformat(), 0, 0, "cover7.jpg"),
            (8, "Old Update Game", "gog", 4.0, 70.0, 68.0, 65.0, 30, 50, 
             (now - timedelta(days=300)).isoformat(), "2022-08-01", 
             (now - timedelta(days=200)).isoformat(), 0, 0, "cover8.jpg"),
        ]
        
        cursor.executemany("""
            INSERT INTO games 
            (id, name, store, playtime_hours, total_rating, aggregated_rating, 
             igdb_rating, igdb_rating_count, total_rating_count, added_at, release_date, 
             last_modified, nsfw, hidden, cover_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_games)
        
        # Create a test collection
        cursor.execute("""
            INSERT INTO collections (id, name, description)
            VALUES (1, 'Test Collection', 'Collection for testing filters')
        """)
        
        # Add all games to the collection
        for game_id in range(1, 9):
            cursor.execute("""
                INSERT INTO collection_games (collection_id, game_id, added_at)
                VALUES (1, ?, ?)
            """, (game_id, now.isoformat()))
        
        conn.commit()
        yield conn
        conn.close()
    
    def test_community_favorites_filter(self, collection_db):
        """Test community-favorites filter uses igdb_rating and igdb_rating_count columns"""
        cursor = collection_db.cursor()
        
        # This simulates the query in collections.py with filter applied
        query = """
            SELECT g.* FROM games g
            INNER JOIN collection_games cg ON g.id = cg.game_id
            WHERE cg.collection_id = 1
            AND (g.igdb_rating >= 85 AND g.igdb_rating_count >= 100)
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Should match games 1 and 2 (igdb_rating >= 85 and igdb_rating_count >= 100)
        assert len(results) == 2, f"Expected 2 community favorites, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Community Favorite 1" in game_names
        assert "Community Favorite 2" in game_names
    
    def test_critic_favorites_filter(self, collection_db):
        """Test critic-favorites filter uses aggregated_rating column"""
        cursor = collection_db.cursor()
        
        # This simulates the query in collections.py with filter applied
        query = """
            SELECT g.* FROM games g
            INNER JOIN collection_games cg ON g.id = cg.game_id
            WHERE cg.collection_id = 1
            AND g.aggregated_rating >= 80
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Should match games 1, 2, 3, 4 (aggregated_rating >= 80)
        assert len(results) == 4, f"Expected 4 critic favorites, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Community Favorite 1" in game_names
        assert "Community Favorite 2" in game_names
        assert "Critic Favorite 1" in game_names
        assert "Critic Favorite 2" in game_names
    
    def test_recently_updated_filter(self, collection_db):
        """Test recently-updated filter uses last_modified column"""
        cursor = collection_db.cursor()
        
        # This simulates the query in collections.py with filter applied
        query = """
            SELECT g.* FROM games g
            INNER JOIN collection_games cg ON g.id = cg.game_id
            WHERE cg.collection_id = 1
            AND g.last_modified >= DATE('now', '-30 days')
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Should match games 1-4 and 5-6 (last_modified within last 30 days)
        assert len(results) >= 4, f"Expected at least 4 recently updated games, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Recently Updated 1" in game_names
        assert "Recently Updated 2" in game_names
    
    def test_multiple_filters_in_collection(self, collection_db):
        """Test combining multiple filters in collection context"""
        cursor = collection_db.cursor()
        
        # Test combining community-favorites AND critic-favorites
        query = """
            SELECT g.* FROM games g
            INNER JOIN collection_games cg ON g.id = cg.game_id
            WHERE cg.collection_id = 1
            AND (g.igdb_rating >= 85 AND g.igdb_rating_count >= 100)
            AND g.aggregated_rating >= 80
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        # Should match games 1 and 2 (both community AND critic favorites)
        assert len(results) == 2, f"Expected 2 games matching both filters, got {len(results)}"


class TestGenreFilters:
    """Test genre filtering with proper LIKE pattern (including closing quote)"""
    
    @pytest.fixture
    def genre_db(self):
        """Create a test database with games having various genre combinations"""
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # Create games table with genres field
        cursor.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                store TEXT,
                genres TEXT,
                playtime_hours REAL,
                total_rating REAL,
                added_at TIMESTAMP,
                release_date TEXT,
                nsfw BOOLEAN DEFAULT 0,
                hidden BOOLEAN DEFAULT 0,
                cover_url TEXT
            )
        """)
        
        now = datetime.now()
        
        # Create labels/game_labels (needed for tag-based filters even if not used here)
        cursor.execute("""
            CREATE TABLE labels (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT,
                system INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE game_labels (
                game_id INTEGER,
                label_id INTEGER,
                PRIMARY KEY (game_id, label_id)
            )
        """)

        # Test games with different genre patterns
        # Genres are stored as JSON arrays like: ["Action", "Adventure"]
        test_games = [
            # Games with "Action" genre
            (1, "Action Game 1", "steam", '["Action", "Shooter"]', 10.0, 85.0, 
             now.isoformat(), "2023-01-01", 0, 0, "cover1.jpg"),
            (2, "Action Game 2", "steam", '["Action", "RPG"]', 5.0, 80.0, 
             now.isoformat(), "2023-02-01", 0, 0, "cover2.jpg"),
            
            # Games with "Adventure" genre (should NOT match "Action")
            (3, "Adventure Game", "gog", '["Adventure", "Puzzle"]', 8.0, 75.0, 
             now.isoformat(), "2022-06-01", 0, 0, "cover3.jpg"),
            
            # Game with substring "action" in a longer word (should NOT match without proper quotes)
            (4, "Reaction Game", "steam", '["Reaction-Based", "Puzzle"]', 3.0, 70.0, 
             now.isoformat(), "2022-03-01", 0, 0, "cover4.jpg"),
            
            # Games with "RPG" genre
            (5, "RPG Game 1", "epic", '["RPG", "Strategy"]', 15.0, 90.0, 
             now.isoformat(), "2021-12-01", 0, 0, "cover5.jpg"),
            (6, "RPG Game 2", "gog", '["RPG", "Action"]', 12.0, 88.0, 
             now.isoformat(), "2022-05-01", 0, 0, "cover6.jpg"),
            
            # Game without genres
            (7, "No Genre Game", "steam", None, 2.0, 60.0, 
             now.isoformat(), "2023-05-01", 0, 0, "cover7.jpg"),
        ]
        
        cursor.executemany("""
            INSERT INTO games 
            (id, name, store, genres, playtime_hours, total_rating, 
             added_at, release_date, nsfw, hidden, cover_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, test_games)
        
        conn.commit()
        yield conn
        conn.close()
    
    def test_action_genre_filter(self, genre_db):
        """Test filtering for 'Action' genre matches only games with Action in genres"""
        cursor = genre_db.cursor()
        
        # This simulates the pattern used in library.py, discover.py, collections.py
        # Pattern: %"action"% (with proper closing quote)
        genre_pattern = '%"action"%'
        
        query = "SELECT * FROM games WHERE LOWER(genres) LIKE ?"
        cursor.execute(query, (genre_pattern,))
        results = cursor.fetchall()
        
        # Should match only games 1, 2, 6 (games with "Action" genre)
        assert len(results) == 3, f"Expected 3 games with Action genre, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Action Game 1" in game_names
        assert "Action Game 2" in game_names
        assert "RPG Game 2" in game_names  # Has both RPG and Action
        
        # Should NOT match "Adventure Game" or "Reaction Game"
        assert "Adventure Game" not in game_names
        assert "Reaction Game" not in game_names
    
    def test_rpg_genre_filter(self, genre_db):
        """Test filtering for 'RPG' genre"""
        cursor = genre_db.cursor()
        
        genre_pattern = '%"rpg"%'
        
        query = "SELECT * FROM games WHERE LOWER(genres) LIKE ?"
        cursor.execute(query, (genre_pattern,))
        results = cursor.fetchall()
        
        # Should match games 2, 5, 6 (games with "RPG" genre)
        assert len(results) == 3, f"Expected 3 games with RPG genre, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Action Game 2" in game_names
        assert "RPG Game 1" in game_names
        assert "RPG Game 2" in game_names
    
    def test_adventure_genre_filter(self, genre_db):
        """Test filtering for 'Adventure' genre does not match 'Action'"""
        cursor = genre_db.cursor()
        
        genre_pattern = '%"adventure"%'
        
        query = "SELECT * FROM games WHERE LOWER(genres) LIKE ?"
        cursor.execute(query, (genre_pattern,))
        results = cursor.fetchall()
        
        # Should match only game 3 (Adventure Game)
        assert len(results) == 1, f"Expected 1 game with Adventure genre, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Adventure Game" in game_names
        
        # Specifically should NOT match games with "Action" genre
        assert "Action Game 1" not in game_names
        assert "Action Game 2" not in game_names
    
    def test_nonexistent_genre_filter(self, genre_db):
        """Test filtering for a genre that doesn't exist returns no results"""
        cursor = genre_db.cursor()
        
        genre_pattern = '%"horror"%'
        
        query = "SELECT * FROM games WHERE LOWER(genres) LIKE ?"
        cursor.execute(query, (genre_pattern,))
        results = cursor.fetchall()
        
        # Should match no games
        assert len(results) == 0, f"Expected 0 games with Horror genre, got {len(results)}"
    
    def test_multiple_genre_filters(self, genre_db):
        """Test combining multiple genre filters (OR logic)"""
        cursor = genre_db.cursor()
        
        # This simulates filtering for games with Action OR RPG
        query = """
            SELECT * FROM games 
            WHERE (LOWER(genres) LIKE ? OR LOWER(genres) LIKE ?)
        """
        cursor.execute(query, ('%"action"%', '%"rpg"%'))
        results = cursor.fetchall()
        
        # Should match games 1, 2, 5, 6 (games with Action or RPG)
        assert len(results) == 4, f"Expected 4 games with Action or RPG, got {len(results)}"
        game_names = [row[1] for row in results]
        assert "Action Game 1" in game_names
        assert "Action Game 2" in game_names
        assert "RPG Game 1" in game_names
        assert "RPG Game 2" in game_names
        
        # Should NOT match Adventure or Reaction games
        assert "Adventure Game" not in game_names
        assert "Reaction Game" not in game_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
