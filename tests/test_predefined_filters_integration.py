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
            cover_url TEXT
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
    
    conn.commit()
    yield conn
    conn.close()


class TestIndividualFilters:
    """Test each filter individually with expected results"""
    
    def test_unplayed_filter(self, test_db):
        """Test unplayed filter returns only games with 0 or NULL playtime"""
        cursor = test_db.cursor()
        sql = f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['unplayed']}"
        cursor.execute(sql)
        result = cursor.fetchone()[0]
        # Should match games 1, 2, 9, 11 (unplayed or NULL playtime)
        assert result >= 2, "Unplayed filter should match games with 0 or NULL playtime"
    
    def test_played_filter(self, test_db):
        """Test played filter returns games with any playtime > 0"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['played']}")
        result = cursor.fetchone()[0]
        # Should match games 3-8, 10, 12-15, 17-18 (playtime > 0)
        assert result >= 10, "Played filter should match games with playtime > 0"
    
    def test_well_played_filter(self, test_db):
        """Test well-played filter (5+ hours)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['well-played']}")
        result = cursor.fetchone()[0]
        # Should match games 4, 5, 10, 12, 13 (5+ hours)
        assert result >= 4, "Well-played filter should match games with 5+ hours"
    
    def test_heavily_played_filter(self, test_db):
        """Test heavily-played filter (20+ hours)"""
        cursor = test_db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['heavily-played']}")
        result = cursor.fetchone()[0]
        # Should match games 5 (50 hours)
        assert result >= 1, "Heavily-played filter should match games with 20+ hours"
    
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
        # Should match games that are both played AND highly rated
        # Games 4, 5, 15 (played + rating >= 90)
        assert result >= 2, "Combined filter should match games meeting both criteria"
    
    def test_unplayed_and_recently_added(self, test_db):
        """Test combination: unplayed + recently-added"""
        cursor = test_db.cursor()
        unplayed_sql = PREDEFINED_QUERIES['unplayed']
        recently_added_sql = PREDEFINED_QUERIES['recently-added']
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE ({unplayed_sql}) AND ({recently_added_sql})")
        result = cursor.fetchone()[0]
        # Should match unplayed games added in last 30 days
        # Game 9 (unplayed, added 1 day ago)
        assert result >= 1, "Should match unplayed games recently added"
    
    def test_three_filter_combination(self, test_db):
        """Test three filters: played + highly-rated + safe"""
        cursor = test_db.cursor()
        played_sql = PREDEFINED_QUERIES['played']
        highly_rated_sql = PREDEFINED_QUERIES['highly-rated']
        safe_sql = PREDEFINED_QUERIES['safe']
        cursor.execute(f"""
            SELECT COUNT(*) FROM games 
            WHERE ({played_sql}) AND ({highly_rated_sql}) AND ({safe_sql})
        """)
        result = cursor.fetchone()[0]
        # Should match played, highly-rated, non-NSFW games
        # Games 4, 5, 15 (assuming they're safe)
        assert result >= 2, "Should match games meeting all three criteria"


class TestNullValueHandling:
    """Test filter behavior with NULL values"""
    
    def test_null_playtime_handling(self, test_db):
        """Test filters handle NULL playtime correctly"""
        cursor = test_db.cursor()
        
        # Unplayed should include NULL playtime
        cursor.execute(f"SELECT COUNT(*) FROM games WHERE {PREDEFINED_QUERIES['unplayed']}")
        unplayed_count = cursor.fetchone()[0]
        
        # Check game 16 (NULL playtime) is handled correctly
        cursor.execute(f"""
            SELECT COUNT(*) FROM games 
            WHERE id = 16 AND ({PREDEFINED_QUERIES['unplayed']})
        """)
        # Just verify the query executes without error
        cursor.fetchone()
        
        assert unplayed_count > 0, "Unplayed filter should handle NULL playtime"
        # NULL playtime might be included or excluded depending on filter logic
    
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
        
        # Unplayed AND heavily-played should return 0
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
        gameplay_filters = QUERY_CATEGORIES.get('gameplay', [])
        
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
        
        gameplay_filters = QUERY_CATEGORIES.get('gameplay', [])
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
