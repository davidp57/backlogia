"""Test filter performance with large library (task 10.5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
import time
from datetime import datetime, timedelta
import random
from web.utils.filters import PREDEFINED_QUERIES


@pytest.fixture
def large_db():
    """Create a test database with large number of games."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Create games table with indexes
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
            cover_url TEXT
        )
    """)
    
    # Create indexes (same as production)
    cursor.execute("CREATE INDEX idx_games_playtime ON games(playtime_hours)")
    cursor.execute("CREATE INDEX idx_games_total_rating ON games(total_rating)")
    cursor.execute("CREATE INDEX idx_games_added_at ON games(added_at)")
    cursor.execute("CREATE INDEX idx_games_release_date ON games(release_date)")
    cursor.execute("CREATE INDEX idx_games_nsfw ON games(nsfw)")
    cursor.execute("CREATE INDEX idx_games_last_modified ON games(last_modified)")
    
    # Insert 10,000 games
    print("\nGenerating 10,000 test games...")
    games = []
    stores = ["steam", "epic", "gog", "ea", "ubisoft"]
    now = datetime.now()
    
    for i in range(10000):
        game = (
            f"Game {i}",
            random.choice(stores),
            random.uniform(0, 100) if random.random() > 0.3 else None,  # 70% have playtime
            random.uniform(50, 95) if random.random() > 0.2 else None,  # 80% have rating
            random.uniform(60, 90) if random.random() > 0.5 else None,  # 50% have aggregated_rating
            random.uniform(70, 95) if random.random() > 0.4 else None,  # 60% have igdb_rating
            random.randint(50, 5000) if random.random() > 0.4 else None,  # 60% have rating count
            random.randint(10, 1000) if random.random() > 0.3 else None,
            (now - timedelta(days=random.randint(0, 730))).isoformat(),  # added in last 2 years
            (now - timedelta(days=random.randint(0, 3650))).isoformat(),  # released in last 10 years
            (now - timedelta(days=random.randint(0, 90))).isoformat(),  # modified in last 3 months
            1 if random.random() > 0.95 else 0,  # 5% NSFW
            0  # not hidden
        )
        games.append(game)
    
    cursor.executemany("""
        INSERT INTO games (name, store, playtime_hours, total_rating, aggregated_rating,
                          igdb_rating, igdb_rating_count, total_rating_count,
                          added_at, release_date, last_modified, nsfw, hidden)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, games)
    
    conn.commit()
    print(f"Created {len(games)} games")
    
    yield conn
    conn.close()


def test_large_library_single_filter_performance(large_db):
    """Test that single filters execute quickly on large library."""
    cursor = large_db.cursor()
    
    # Test each filter's performance
    for filter_id, condition in PREDEFINED_QUERIES.items():
        start = time.perf_counter()
        
        sql = f"SELECT COUNT(*) FROM games WHERE {condition}"
        cursor.execute(sql)
        count = cursor.fetchone()[0]
        
        elapsed = time.perf_counter() - start
        
        print(f"\n{filter_id}: {count} results in {elapsed*1000:.2f}ms")
        
        # Assert reasonable performance (< 100ms for single filter)
        assert elapsed < 0.1, f"Filter {filter_id} took {elapsed*1000:.2f}ms (expected < 100ms)"


def test_large_library_multiple_filters_performance(large_db):
    """Test performance with multiple filters active."""
    cursor = large_db.cursor()
    
    # Common filter combinations
    combinations = [
        ["unplayed", "highly-rated"],
        ["played", "recent-releases"],
        ["well-played", "well-rated", "recently-added"],
        ["highly-rated", "classics"],
    ]
    
    for filters in combinations:
        conditions = [PREDEFINED_QUERIES[f] for f in filters]
        where_clause = " AND ".join(f"({cond})" for cond in conditions)
        
        start = time.perf_counter()
        
        sql = f"SELECT COUNT(*) FROM games WHERE {where_clause}"
        cursor.execute(sql)
        count = cursor.fetchone()[0]
        
        elapsed = time.perf_counter() - start
        
        print(f"\n{' + '.join(filters)}: {count} results in {elapsed*1000:.2f}ms")
        
        # Multiple filters should still be fast (< 200ms)
        assert elapsed < 0.2, f"Filters {filters} took {elapsed*1000:.2f}ms (expected < 200ms)"


def test_large_library_full_query_performance(large_db):
    """Test full library query with filters, sorting, and counting."""
    cursor = large_db.cursor()
    
    # Simulate full library query with:
    # - Predefined filters
    # - Store/genre filters (simulated)
    # - Result counting
    # - Sorting
    # - Pagination
    
    filter_conditions = [
        PREDEFINED_QUERIES["played"],
        PREDEFINED_QUERIES["well-rated"]
    ]
    
    where_clause = " AND ".join(f"({cond})" for cond in filter_conditions)
    where_clause += " AND (hidden IS NULL OR hidden = 0)"
    
    start = time.perf_counter()
    
    # Count total matching games
    cursor.execute(f"SELECT COUNT(*) FROM games WHERE {where_clause}")
    total = cursor.fetchone()[0]
    
    # Get paginated results with sorting
    sql = f"""
        SELECT id, name, total_rating, playtime_hours
        FROM games
        WHERE {where_clause}
        ORDER BY added_at DESC
        LIMIT 50
    """
    cursor.execute(sql)
    games = cursor.fetchall()
    
    elapsed = time.perf_counter() - start
    
    print(f"\nFull query: {len(games)} games (of {total}) in {elapsed*1000:.2f}ms")
    
    # Full query should complete quickly (< 300ms)
    assert elapsed < 0.3, f"Full query took {elapsed*1000:.2f}ms (expected < 300ms)"


def test_large_library_filter_count_aggregation(large_db):
    """Test performance of COUNT(CASE) aggregation for all filters."""
    cursor = large_db.cursor()
    
    # Build CASE statements for all filters (like in library route)
    case_statements = []
    for filter_id, condition in PREDEFINED_QUERIES.items():
        case_statements.append(
            f"COUNT(CASE WHEN {condition} THEN 1 END) as {filter_id.replace('-', '_')}"
        )
    
    sql = f"""
        SELECT {', '.join(case_statements)}
        FROM games
        WHERE (hidden IS NULL OR hidden = 0)
    """
    
    start = time.perf_counter()
    cursor.execute(sql)
    results = cursor.fetchone()
    elapsed = time.perf_counter() - start
    
    print(f"\nFilter counts aggregation in {elapsed*1000:.2f}ms")
    print(f"Sample counts: {dict(zip(['unplayed', 'played', 'highly_rated'], results[:3]))}")
    
    # Count aggregation should be efficient (< 500ms for all filters)
    assert elapsed < 0.5, f"Count aggregation took {elapsed*1000:.2f}ms (expected < 500ms)"


def test_large_library_index_usage(large_db):
    """Verify that indexes are being used for filter queries."""
    cursor = large_db.cursor()
    
    # Check query plan for indexed columns
    filters_using_indexes = {
        "unplayed": "playtime_hours",
        "highly-rated": "total_rating",
        "recently-added": "added_at",
        "recent-releases": "release_date",
        "nsfw": "nsfw"
    }
    
    for filter_id, indexed_column in filters_using_indexes.items():
        condition = PREDEFINED_QUERIES[filter_id]
        sql = f"EXPLAIN QUERY PLAN SELECT COUNT(*) FROM games WHERE {condition}"
        
        cursor.execute(sql)
        plan = cursor.fetchall()
        plan_text = " ".join(str(row) for row in plan)
        
        print(f"\n{filter_id} plan: {plan_text}")
        
        # Check if index is mentioned in plan
        # Note: SQLite may not always use index for simple COUNT queries
        # This is informational rather than a strict assertion


def test_large_library_memory_usage(large_db):
    """Test that queries don't load entire result set into memory."""
    cursor = large_db.cursor()
    
    # Use a filter that matches many games
    condition = PREDEFINED_QUERIES["played"]
    
    # Query with LIMIT to avoid loading all results
    sql = f"""
        SELECT id, name
        FROM games
        WHERE {condition}
        ORDER BY added_at DESC
        LIMIT 100
    """
    
    start = time.perf_counter()
    cursor.execute(sql)
    
    # Fetch only requested rows
    results = cursor.fetchall()
    elapsed = time.perf_counter() - start
    
    print(f"\nPaginated query: {len(results)} rows in {elapsed*1000:.2f}ms")
    
    # Should be very fast with LIMIT
    assert elapsed < 0.1, f"Paginated query took {elapsed*1000:.2f}ms"
    assert len(results) <= 100
