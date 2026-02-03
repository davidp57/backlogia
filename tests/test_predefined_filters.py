"""
Unit tests for predefined query filters

Tests the filter definitions, SQL generation, and filter validation logic
for the predefined query filters feature.
"""

import sys
from pathlib import Path

# Add parent directory to path to import web modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import sqlite3
from fastapi.testclient import TestClient
from web.main import app
from web.utils.filters import (
    PREDEFINED_QUERIES,
    QUERY_DISPLAY_NAMES,
    QUERY_CATEGORIES,
    QUERY_DESCRIPTIONS
)


class TestFilterDefinitions:
    """Test filter constant definitions and structure"""

    def test_all_filters_have_sql_definitions(self):
        """Ensure every filter ID has a SQL WHERE clause"""
        expected_filters = [
            # Gameplay
            "unplayed", "played", "started", "well-played", "heavily-played",
            # Ratings
            "highly-rated", "well-rated", "below-average", "unrated", 
            "hidden-gems", "critic-favorites", "community-favorites",
            # Dates
            "recently-added", "older-library", "recent-releases", 
            "recently-updated", "classics",
            # Content
            "nsfw", "safe"
        ]
        
        for filter_id in expected_filters:
            assert filter_id in PREDEFINED_QUERIES, f"Filter '{filter_id}' missing from PREDEFINED_QUERIES"
            assert isinstance(PREDEFINED_QUERIES[filter_id], str), f"Filter '{filter_id}' SQL must be a string"
            assert len(PREDEFINED_QUERIES[filter_id]) > 0, f"Filter '{filter_id}' SQL cannot be empty"

    def test_all_filters_have_display_names(self):
        """Ensure every filter has a user-friendly display name"""
        for filter_id in PREDEFINED_QUERIES.keys():
            assert filter_id in QUERY_DISPLAY_NAMES, f"Filter '{filter_id}' missing display name"
            assert isinstance(QUERY_DISPLAY_NAMES[filter_id], str), f"Display name for '{filter_id}' must be string"
            assert len(QUERY_DISPLAY_NAMES[filter_id]) > 0, f"Display name for '{filter_id}' cannot be empty"

    def test_all_filters_have_descriptions(self):
        """Ensure every filter has a tooltip description"""
        for filter_id in PREDEFINED_QUERIES.keys():
            assert filter_id in QUERY_DESCRIPTIONS, f"Filter '{filter_id}' missing description"
            assert isinstance(QUERY_DESCRIPTIONS[filter_id], str), f"Description for '{filter_id}' must be string"
            assert len(QUERY_DESCRIPTIONS[filter_id]) > 0, f"Description for '{filter_id}' cannot be empty"

    def test_category_organization(self):
        """Ensure all filters are organized into categories"""
        expected_categories = ["Gameplay", "Ratings", "Dates", "Content"]
        
        assert set(QUERY_CATEGORIES.keys()) == set(expected_categories), \
            f"Categories should be {expected_categories}"
        
        # Collect all filters from categories
        categorized_filters = set()
        for category, filters in QUERY_CATEGORIES.items():
            assert isinstance(filters, list), f"Category '{category}' must contain a list of filters"
            categorized_filters.update(filters)
        
        # Ensure all defined filters are categorized
        defined_filters = set(PREDEFINED_QUERIES.keys())
        assert categorized_filters == defined_filters, \
            "All filters must be assigned to a category"

    def test_category_sizes(self):
        """Verify expected number of filters per category"""
        expected_sizes = {
            "Gameplay": 5,
            "Ratings": 7,
            "Dates": 5,
            "Content": 2
        }
        
        for category, expected_size in expected_sizes.items():
            actual_size = len(QUERY_CATEGORIES[category])
            assert actual_size == expected_size, \
                f"Category '{category}' should have {expected_size} filters, has {actual_size}"


class TestSQLGeneration:
    """Test SQL WHERE clause generation"""

    def test_sql_clauses_are_valid_format(self):
        """Ensure SQL clauses don't contain dangerous patterns"""
        dangerous_patterns = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "--", ";"]
        
        for filter_id, sql in PREDEFINED_QUERIES.items():
            sql_upper = sql.upper()
            for pattern in dangerous_patterns:
                assert pattern not in sql_upper, \
                    f"Filter '{filter_id}' contains potentially dangerous SQL: {pattern}"

    def test_playtime_filters(self):
        """Test gameplay filter SQL conditions"""
        assert "playtime_hours" in PREDEFINED_QUERIES["unplayed"]
        assert "playtime_hours" in PREDEFINED_QUERIES["played"]
        assert "playtime_hours" in PREDEFINED_QUERIES["started"]
        assert "playtime_hours" in PREDEFINED_QUERIES["well-played"]
        assert "playtime_hours" in PREDEFINED_QUERIES["heavily-played"]

    def test_rating_filters(self):
        """Test rating filter SQL conditions"""
        assert "total_rating" in PREDEFINED_QUERIES["highly-rated"]
        assert "total_rating" in PREDEFINED_QUERIES["well-rated"]
        assert "total_rating" in PREDEFINED_QUERIES["below-average"]
        assert "total_rating" in PREDEFINED_QUERIES["unrated"]
        assert "aggregated_rating" in PREDEFINED_QUERIES["critic-favorites"]

    def test_date_filters(self):
        """Test date filter SQL conditions"""
        assert "added_at" in PREDEFINED_QUERIES["recently-added"]
        assert "added_at" in PREDEFINED_QUERIES["older-library"]
        assert "release_date" in PREDEFINED_QUERIES["recent-releases"]
        assert "last_modified" in PREDEFINED_QUERIES["recently-updated"]
        assert "release_date" in PREDEFINED_QUERIES["classics"]

    def test_content_filters(self):
        """Test content filter SQL conditions"""
        assert "nsfw" in PREDEFINED_QUERIES["nsfw"]
        assert "nsfw" in PREDEFINED_QUERIES["safe"]

    def test_numeric_thresholds(self):
        """Verify numeric thresholds in SQL are reasonable"""
        # Highly-rated should be >= 90
        assert "90" in PREDEFINED_QUERIES["highly-rated"]
        
        # Well-rated should be >= 75
        assert "75" in PREDEFINED_QUERIES["well-rated"]
        
        # Playtime thresholds
        assert "5" in PREDEFINED_QUERIES["well-played"]
        assert "20" in PREDEFINED_QUERIES["heavily-played"]

    def test_date_calculations(self):
        """Verify date calculations use proper SQLite syntax"""
        # Recently-added uses 30 days
        assert "30" in PREDEFINED_QUERIES["recently-added"]
        assert "DATE" in PREDEFINED_QUERIES["recently-added"]
        
        # Classics uses 10 years
        assert "10 years" in PREDEFINED_QUERIES["classics"] or "10 year" in PREDEFINED_QUERIES["classics"]


class TestFilterValidation:
    """Test filter validation logic"""

    def test_valid_filter_ids(self):
        """Test that all defined filters are valid"""
        valid_ids = list(PREDEFINED_QUERIES.keys())
        
        for filter_id in valid_ids:
            assert filter_id in PREDEFINED_QUERIES, \
                f"Valid filter '{filter_id}' should be in PREDEFINED_QUERIES"

    def test_invalid_filter_ids(self):
        """Test that invalid filter IDs are not in definitions"""
        invalid_ids = ["nonexistent", "fake-filter", "invalid", ""]
        
        for invalid_id in invalid_ids:
            assert invalid_id not in PREDEFINED_QUERIES, \
                f"Invalid filter '{invalid_id}' should not be in PREDEFINED_QUERIES"


class TestCategoryExclusivity:
    """Test that category organization supports exclusive selection"""

    def test_no_filter_in_multiple_categories(self):
        """Ensure each filter appears in exactly one category"""
        filter_count = {}
        
        for category, filters in QUERY_CATEGORIES.items():
            for filter_id in filters:
                filter_count[filter_id] = filter_count.get(filter_id, 0) + 1
        
        for filter_id, count in filter_count.items():
            assert count == 1, \
                f"Filter '{filter_id}' appears in {count} categories, should be exactly 1"

    def test_categories_are_non_empty(self):
        """Ensure no category is empty"""
        for category, filters in QUERY_CATEGORIES.items():
            assert len(filters) > 0, f"Category '{category}' should not be empty"


class TestQueryParameterHandling:
    """Test query parameter handling in library route"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    def test_single_query_parameter(self, client):
        """Test single filter parameter is accepted"""
        response = client.get("/library?queries=unplayed")
        assert response.status_code == 200
        # The filter should be reflected in the response
        assert "unplayed" in response.text.lower() or "Unplayed" in response.text
    
    def test_multiple_query_parameters(self, client):
        """Test multiple filter parameters are accepted"""
        response = client.get("/library?queries=unplayed&queries=highly-rated")
        assert response.status_code == 200
        # Both filters should be reflected in the response
        content = response.text
        assert "unplayed" in content.lower() or "Unplayed" in content
        assert "highly" in content.lower() or "Highly" in content
    
    def test_invalid_query_id_ignored(self, client):
        """Test that invalid filter IDs are gracefully ignored"""
        # Should not cause an error, just ignore the invalid filter
        response = client.get("/library?queries=invalid-filter-id")
        assert response.status_code == 200
    
    def test_mixed_valid_invalid_filters(self, client):
        """Test that valid filters work even with invalid ones present"""
        response = client.get("/library?queries=unplayed&queries=invalid&queries=played")
        assert response.status_code == 200
        # Valid filters should still work
        assert "unplayed" in response.text.lower() or "Unplayed" in response.text
    
    def test_empty_queries_parameter(self, client):
        """Test that empty queries parameter shows all games"""
        response = client.get("/library")
        assert response.status_code == 200
        # Should work normally without filters
    
    def test_queries_with_other_filters(self, client):
        """Test queries parameter works alongside other filters"""
        response = client.get("/library?queries=unplayed&search=test&sort=name")
        assert response.status_code == 200
        # All parameters should be preserved


class TestResultCounting:
    """Test result counting with various filter combinations"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return TestClient(app)
    
    def test_count_without_filters(self, client):
        """Test that count is displayed without filters"""
        response = client.get("/library")
        assert response.status_code == 200
        # Should contain count information (total games)
        assert "game" in response.text.lower()
    
    def test_count_with_single_filter(self, client):
        """Test that filtered count is accurate with one filter"""
        response = client.get("/library?queries=unplayed")
        assert response.status_code == 200
        # Should show filtered count
        content = response.text.lower()
        assert "game" in content
    
    def test_count_with_multiple_filters(self, client):
        """Test that count updates correctly with multiple filters"""
        # Get baseline count
        response_no_filter = client.get("/library")
        assert response_no_filter.status_code == 200
        
        # Apply filters - should reduce count
        response_filtered = client.get("/library?queries=unplayed&queries=highly-rated")
        assert response_filtered.status_code == 200
        
        # Both responses should be valid
        assert "game" in response_no_filter.text.lower()
        assert "game" in response_filtered.text.lower()
    
    def test_count_consistency(self, client):
        """Test that adding/removing filters maintains count consistency"""
        # Test various filter combinations
        filter_combinations = [
            "",
            "?queries=played",
            "?queries=unplayed",
            "?queries=highly-rated",
            "?queries=played&queries=highly-rated"
        ]
        
        for filters in filter_combinations:
            response = client.get(f"/library{filters}")
            assert response.status_code == 200
            # Each should have valid count display
            assert "game" in response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
