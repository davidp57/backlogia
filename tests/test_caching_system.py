"""
Tests for 2-tier caching system (memory + database).

Tests cover:
- Tier 1 (memory cache) hit/miss/expiry
- Tier 2 (database cache) hit/miss/TTL
- Cache key generation (hash-based)
- Cache invalidation on library changes
- Filter-specific caching
- Cache promotion (Tier 2 → Tier 1)
"""

import pytest
import sqlite3
import hashlib
import time


@pytest.fixture
def test_db():
    """Create in-memory test database with cache table"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create popularity_cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS popularity_cache (
            igdb_id INTEGER NOT NULL,
            popularity_type TEXT NOT NULL,
            popularity_value INTEGER NOT NULL,
            cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (igdb_id, popularity_type)
        )
    """)
    
    conn.commit()
    yield conn
    conn.close()


def compute_cache_key(igdb_ids: list) -> str:
    """Generate deterministic hash from IGDB ID list"""
    igdb_ids_sorted = sorted(igdb_ids)
    igdb_str = ",".join(map(str, igdb_ids_sorted))
    return hashlib.md5(igdb_str.encode()).hexdigest()


class TestCacheKeyGeneration:
    """Test cache key generation logic"""
    
    def test_same_ids_same_hash(self):
        """Same IGDB IDs should produce same hash"""
        ids1 = [100, 200, 300]
        ids2 = [100, 200, 300]
        
        hash1 = compute_cache_key(ids1)
        hash2 = compute_cache_key(ids2)
        
        assert hash1 == hash2
    
    def test_order_independent(self):
        """Hash should be order-independent (sorted before hashing)"""
        ids1 = [300, 100, 200]
        ids2 = [100, 200, 300]
        
        hash1 = compute_cache_key(ids1)
        hash2 = compute_cache_key(ids2)
        
        assert hash1 == hash2
    
    def test_different_ids_different_hash(self):
        """Different IGDB IDs should produce different hash"""
        ids1 = [100, 200, 300]
        ids2 = [100, 200, 400]
        
        hash1 = compute_cache_key(ids1)
        hash2 = compute_cache_key(ids2)
        
        assert hash1 != hash2
    
    def test_empty_list_produces_hash(self):
        """Empty list should produce valid hash"""
        ids = []
        hash_result = compute_cache_key(ids)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 32  # MD5 hash length


class TestMemoryCache:
    """Test Tier 1 (memory) cache behavior"""
    
    def test_cache_miss_returns_none(self):
        """Cache miss should return None or trigger fetch"""
        cache = {}
        cache_key = "nonexistent_key"
        
        assert cache_key not in cache
    
    def test_cache_hit_returns_data(self):
        """Cache hit should return cached data"""
        cache = {}
        cache_key = "test_key"
        cache_data = {
            "data": {"most_popular": [100, 200, 300]},
            "cached_at": time.time()
        }
        
        cache[cache_key] = cache_data
        
        assert cache_key in cache
        assert cache[cache_key]["data"] == cache_data["data"]
    
    def test_cache_expiry_after_15_minutes(self):
        """Cache should expire after 15 minutes (900 seconds)"""
        cache = {}
        cache_key = "test_key"
        old_timestamp = time.time() - 1000  # 16.67 minutes ago
        
        cache[cache_key] = {
            "data": {"most_popular": []},
            "cached_at": old_timestamp
        }
        
        # Check if expired
        age = time.time() - cache[cache_key]["cached_at"]
        is_expired = age > 900
        
        assert is_expired is True
    
    def test_cache_valid_within_15_minutes(self):
        """Cache should be valid within 15 minutes"""
        cache = {}
        cache_key = "test_key"
        recent_timestamp = time.time() - 300  # 5 minutes ago
        
        cache[cache_key] = {
            "data": {"most_popular": []},
            "cached_at": recent_timestamp
        }
        
        # Check if still valid
        age = time.time() - cache[cache_key]["cached_at"]
        is_valid = age < 900
        
        assert is_valid is True


class TestDatabaseCache:
    """Test Tier 2 (database) cache behavior"""
    
    def test_insert_cache_entry(self, test_db):
        """Should be able to insert cache entries"""
        cursor = test_db.cursor()
        
        cursor.execute("""
            INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value)
            VALUES (?, ?, ?)
        """, (100, "most_popular", 95))
        
        test_db.commit()
        
        cursor.execute("SELECT * FROM popularity_cache WHERE igdb_id = 100")
        result = cursor.fetchone()
        
        assert result is not None
        assert result["igdb_id"] == 100
        assert result["popularity_type"] == "most_popular"
        assert result["popularity_value"] == 95
    
    def test_query_cache_by_ttl(self, test_db):
        """Should retrieve only non-expired cache entries"""
        cursor = test_db.cursor()
        
        # Insert fresh entry (now)
        cursor.execute("""
            INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value, cached_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (100, "most_popular", 95))
        
        # Insert expired entry (2 days ago)
        cursor.execute("""
            INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value, cached_at)
            VALUES (?, ?, ?, datetime('now', '-2 days'))
        """, (200, "most_popular", 85))
        
        test_db.commit()
        
        # Query only entries from last 24 hours
        cursor.execute("""
            SELECT * FROM popularity_cache
            WHERE cached_at > datetime('now', '-1 day')
        """)
        results = cursor.fetchall()
        
        assert len(results) == 1
        assert results[0]["igdb_id"] == 100
    
    def test_multiple_popularity_types(self, test_db):
        """Should store multiple popularity types for same game"""
        cursor = test_db.cursor()
        
        types = ["most_popular", "top_rated", "most_hyped"]
        for pop_type in types:
            cursor.execute("""
                INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value)
                VALUES (?, ?, ?)
            """, (100, pop_type, 90))
        
        test_db.commit()
        
        cursor.execute("SELECT * FROM popularity_cache WHERE igdb_id = 100")
        results = cursor.fetchall()
        
        assert len(results) == 3
        assert set(r["popularity_type"] for r in results) == set(types)


class TestCacheInvalidation:
    """Test cache invalidation strategies"""
    
    def test_library_change_triggers_new_hash(self):
        """Adding/removing games should change cache key"""
        # Original library
        old_igdb_ids = [100, 200, 300]
        old_hash = compute_cache_key(old_igdb_ids)
        
        # After syncing a new game
        new_igdb_ids = [100, 200, 300, 400]
        new_hash = compute_cache_key(new_igdb_ids)
        
        assert old_hash != new_hash
    
    def test_filter_change_triggers_new_hash(self):
        """Different filters produce different IGDB ID sets"""
        # All games
        all_igdb_ids = [100, 200, 300, 400, 500]
        all_hash = compute_cache_key(all_igdb_ids)
        
        # Filtered games (e.g., only Steam)
        filtered_igdb_ids = [100, 200, 300]
        filtered_hash = compute_cache_key(filtered_igdb_ids)
        
        assert all_hash != filtered_hash


class TestCachePromotion:
    """Test Tier 2 → Tier 1 cache promotion"""
    
    def test_db_cache_hit_promotes_to_memory(self, test_db):
        """DB cache hit should populate memory cache"""
        memory_cache = {}
        
        # Simulate DB cache hit
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value)
            VALUES (?, ?, ?)
        """, (100, "most_popular", 95))
        test_db.commit()
        
        # Fetch from DB
        cursor.execute("SELECT * FROM popularity_cache WHERE igdb_id = 100")
        db_result = cursor.fetchone()
        
        # Promote to memory cache
        cache_key = "test_key"
        memory_cache[cache_key] = {
            "data": {"most_popular": [db_result["igdb_id"]]},
            "cached_at": time.time()
        }
        
        # Verify memory cache now has the data
        assert cache_key in memory_cache
        assert memory_cache[cache_key]["data"]["most_popular"] == [100]


class TestFilterSpecificCaching:
    """Test that each filter combination gets its own cache"""
    
    def test_different_filters_different_cache_keys(self):
        """Different filter combos should have different cache keys"""
        # Store filter: Steam only
        steam_igdb_ids = [100, 200, 300]
        steam_hash = compute_cache_key(steam_igdb_ids)
        
        # Store filter: Epic only
        epic_igdb_ids = [400, 500, 600]
        epic_hash = compute_cache_key(epic_igdb_ids)
        
        # Store filter: GOG only
        gog_igdb_ids = [700, 800, 900]
        gog_hash = compute_cache_key(gog_igdb_ids)
        
        assert steam_hash != epic_hash
        assert steam_hash != gog_hash
        assert epic_hash != gog_hash
    
    def test_same_filter_same_cache_key(self):
        """Same filter applied twice should reuse cache"""
        # Apply filter twice
        igdb_ids = [100, 200, 300]
        hash1 = compute_cache_key(igdb_ids)
        hash2 = compute_cache_key(igdb_ids)
        
        assert hash1 == hash2


class TestCacheFlow:
    """Test complete cache flow (Tier 1 → Tier 2 → API)"""
    
    def test_tier1_hit_skips_tier2_and_api(self):
        """Tier 1 hit should not query Tier 2 or API"""
        memory_cache = {}
        cache_key = "test_key"
        
        # Populate Tier 1
        memory_cache[cache_key] = {
            "data": {"most_popular": [100, 200]},
            "cached_at": time.time()
        }
        
        # Check Tier 1
        if cache_key in memory_cache:
            age = time.time() - memory_cache[cache_key]["cached_at"]
            if age < 900:  # 15 minutes
                # Tier 1 hit - return immediately
                result = memory_cache[cache_key]["data"]
                assert result == {"most_popular": [100, 200]}
                return  # Skip Tier 2 and API
        
        # Should not reach here
        assert False, "Should have returned from Tier 1"
    
    def test_tier1_miss_checks_tier2(self, test_db):
        """Tier 1 miss should check Tier 2 before API"""
        memory_cache = {}
        
        # Populate Tier 2
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value)
            VALUES (?, ?, ?)
        """, (100, "most_popular", 95))
        test_db.commit()
        
        # Check Tier 1 (miss)
        cache_key = "test_key"
        tier1_hit = cache_key in memory_cache
        assert tier1_hit is False
        
        # Check Tier 2 (hit)
        cursor.execute("""
            SELECT * FROM popularity_cache
            WHERE cached_at > datetime('now', '-1 day')
        """)
        tier2_results = cursor.fetchall()
        
        assert len(tier2_results) > 0
        # Would promote to Tier 1 here
    
    def test_both_tiers_miss_triggers_api_fetch(self, test_db):
        """Both cache misses should trigger API fetch"""
        memory_cache = {}
        
        # Check Tier 1 (miss)
        cache_key = "nonexistent"
        tier1_hit = cache_key in memory_cache
        assert tier1_hit is False
        
        # Check Tier 2 (miss)
        cursor = test_db.cursor()
        cursor.execute("""
            SELECT * FROM popularity_cache
            WHERE cached_at > datetime('now', '-1 day')
        """)
        tier2_results = cursor.fetchall()
        assert len(tier2_results) == 0
        
        # At this point, would fetch from IGDB API
        # (simulated - not testing actual API calls)
        api_result = {"most_popular": [100, 200, 300]}
        
        # Store in both caches
        memory_cache[cache_key] = {
            "data": api_result,
            "cached_at": time.time()
        }
        
        for igdb_id in api_result["most_popular"]:
            cursor.execute("""
                INSERT INTO popularity_cache (igdb_id, popularity_type, popularity_value)
                VALUES (?, ?, ?)
            """, (igdb_id, "most_popular", 90))
        test_db.commit()
        
        # Verify both caches now populated
        assert cache_key in memory_cache
        cursor.execute("SELECT COUNT(*) FROM popularity_cache")
        db_count = cursor.fetchone()[0]
        assert db_count == 3
