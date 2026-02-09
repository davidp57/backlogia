"""
Unit tests for query filter OR/AND logic

Tests that filters within the same category are combined with OR,
and filters from different categories are combined with AND.
"""

import sys
from pathlib import Path

# Add parent directory to path to import web modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from web.utils.filters import build_query_filter_sql


class TestQueryFilterLogic:
    """Test the OR/AND logic for combining query filters"""
    
    def test_single_filter(self):
        """Test a single filter returns its SQL condition"""
        result = build_query_filter_sql(['played'])
        assert 'playtime_hours > 0' in result
        assert ' OR ' not in result
        assert ' AND ' not in result
    
    def test_multiple_filters_same_category(self):
        """Test multiple filters in same category are combined with OR"""
        result = build_query_filter_sql(['played', 'started'])
        
        # Should contain both conditions
        assert 'playtime_hours > 0' in result
        assert 'playtime_hours < 5' in result
        
        # Should be combined with OR
        assert ' OR ' in result
        # Should NOT have AND at the top level (only within individual conditions)
        # Count ANDs - should only be the one inside "started" condition
        and_count = result.count(' AND ')
        assert and_count <= 2  # One in "started" condition itself
    
    def test_multiple_filters_different_categories(self):
        """Test filters from different categories are combined with AND"""
        result = build_query_filter_sql(['played', 'highly-rated'])
        
        # Should contain both conditions
        assert 'playtime_hours > 0' in result
        assert 'total_rating >= 90' in result
        
        # Should be combined with AND (between categories)
        assert ' AND ' in result
        # Should NOT have OR (different categories)
        assert ' OR ' not in result
    
    def test_complex_combination(self):
        """Test combination of multiple filters across multiple categories"""
        # 2 from Gameplay, 2 from Ratings
        result = build_query_filter_sql(['played', 'started', 'highly-rated', 'well-rated'])
        
        # Should contain all conditions
        assert 'playtime_hours > 0' in result
        assert 'total_rating >= 90' in result
        assert 'total_rating >= 75' in result
        
        # Should have both OR (within categories) and AND (between categories)
        assert ' OR ' in result
        assert ' AND ' in result
        
        # Structure should be: (gameplay_condition1 OR gameplay_condition2) AND (rating_condition1 OR rating_condition2)
        # Verify parentheses are balanced
        assert result.count('(') == result.count(')')
    
    def test_with_table_prefix(self):
        """Test that table prefix is correctly applied to column names"""
        result = build_query_filter_sql(['played'], table_prefix='g.')
        
        # Should have prefixed column names
        assert 'g.playtime_hours > 0' in result
        # Make sure we're using the prefix (not checking for unprefixed as substring)
        assert result.count('g.playtime_hours') > 0
    
    def test_empty_list(self):
        """Test that empty query list returns empty string"""
        result = build_query_filter_sql([])
        assert result == ""
    
    def test_invalid_queries_filtered(self):
        """Test that invalid query IDs are filtered out"""
        result = build_query_filter_sql(['played', 'invalid-query-id', 'highly-rated'])
        
        # Should only contain valid filters
        assert 'playtime_hours > 0' in result
        assert 'total_rating >= 90' in result
        # Should still work with AND
        assert ' AND ' in result
    
    def test_all_filters_from_one_category(self):
        """Test selecting many filters from one category (Gameplay)"""
        result = build_query_filter_sql(['unplayed', 'played', 'started', 'well-played', 'heavily-played'])
        
        # Should have ORs but no top-level ANDs (all same category)
        assert ' OR ' in result
        
    def test_dates_and_content_categories(self):
        """Test filters from Dates and Content categories"""
        result = build_query_filter_sql(['recently-added', 'nsfw'])
        
        # Should contain both conditions
        assert 'added_at >=' in result or 'DATE' in result
        assert 'nsfw = 1' in result
        
        # Different categories, should have AND
        assert ' AND ' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
