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
from web.utils.filters import build_query_filter_sql, _apply_prefix


class TestQueryFilterLogic:
    """Test the OR/AND logic for combining query filters"""

    def test_single_filter(self):
        """Test a single filter returns its SQL condition"""
        result = build_query_filter_sql(['played'])
        assert 'game_labels' in result
        assert 'Played' in result
        assert ' OR ' not in result

    def test_multiple_filters_same_category(self):
        """Test multiple filters in same category are combined with OR"""
        result = build_query_filter_sql(['played', 'just-tried'])

        # Should contain both conditions (tag-based)
        assert 'Played' in result
        assert 'Just Tried' in result

        # Should be combined with OR
        assert ' OR ' in result

    def test_multiple_filters_different_categories(self):
        """Test filters from different categories are combined with AND"""
        result = build_query_filter_sql(['played', 'highly-rated'])

        # Should contain both conditions
        assert 'game_labels' in result  # played uses tags
        assert 'total_rating >= 90' in result

        # Should be combined with AND (between categories)
        assert ' AND ' in result

    def test_complex_combination(self):
        """Test combination of multiple filters across multiple categories"""
        # 2 from Gameplay, 2 from Ratings
        result = build_query_filter_sql(['played', 'just-tried', 'highly-rated', 'well-rated'])

        # Should contain all conditions
        assert 'Played' in result
        assert 'Just Tried' in result
        assert 'total_rating >= 90' in result
        assert 'total_rating >= 75' in result

        # Should have both OR (within categories) and AND (between categories)
        assert ' OR ' in result
        assert ' AND ' in result

        # Verify parentheses are balanced
        assert result.count('(') == result.count(')')

    def test_with_table_prefix(self):
        """Test that table prefix is correctly applied to column names"""
        result = build_query_filter_sql(['highly-rated'], table_prefix='g.')

        # Should have prefixed column names
        assert 'g.total_rating >= 90' in result

    def test_prefix_replaces_games_id(self):
        """Test that games.id is replaced with prefix in tag-based filters"""
        result = build_query_filter_sql(['played'], table_prefix='g.')

        # games.id should become g.id in the subquery
        assert 'g.id' in result
        assert 'games.id' not in result

    def test_prefix_replaces_games_store(self):
        """Test that games.store is replaced with prefix in unplayed filter"""
        result = build_query_filter_sql(['unplayed'], table_prefix='g.')

        # games.store should become g.store
        assert "g.store = 'steam'" in result
        assert "g.store != 'steam'" in result
        assert 'games.store' not in result

    def test_prefix_replaces_games_priority(self):
        """Test that games.priority is replaced with prefix"""
        result = build_query_filter_sql(['has-priority'], table_prefix='g.')
        assert 'g.priority' in result
        assert 'games.priority' not in result

    def test_prefix_replaces_games_personal_rating(self):
        """Test that games.personal_rating is replaced with prefix"""
        result = build_query_filter_sql(['personally-rated'], table_prefix='g.')
        assert 'g.personal_rating' in result
        assert 'games.personal_rating' not in result

    def test_empty_list(self):
        """Test that empty query list returns empty string"""
        result = build_query_filter_sql([])
        assert result == ""

    def test_invalid_queries_filtered(self):
        """Test that invalid query IDs are filtered out"""
        result = build_query_filter_sql(['played', 'invalid-query-id', 'highly-rated'])

        # Should only contain valid filters
        assert 'game_labels' in result
        assert 'total_rating >= 90' in result
        # Should still work with AND
        assert ' AND ' in result

    def test_all_filters_from_one_category(self):
        """Test selecting many filters from one category (Gameplay)"""
        result = build_query_filter_sql(['unplayed', 'played', 'just-tried', 'well-played', 'heavily-played'])

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

    def test_my_rating_category_or_logic(self):
        """Test My Rating filters within same category use OR"""
        result = build_query_filter_sql(['has-priority', 'personally-rated'])

        assert 'priority' in result
        assert 'personal_rating' in result
        assert ' OR ' in result

    def test_my_rating_cross_category_and_logic(self):
        """Test My Rating filters combined with other categories use AND"""
        result = build_query_filter_sql(['has-priority', 'highly-rated'])

        assert 'priority' in result
        assert 'total_rating >= 90' in result
        assert ' AND ' in result

    def test_unplayed_filter_contains_steam_distinction(self):
        """Test that the unplayed filter SQL distinguishes Steam from non-Steam"""
        result = build_query_filter_sql(['unplayed'])
        assert "games.store = 'steam'" in result
        assert "games.store != 'steam'" in result
        assert "Never Launched" in result


class TestApplyPrefix:
    """Test the _apply_prefix helper function"""

    def test_no_prefix(self):
        """Test that no prefix returns SQL unchanged"""
        sql = "total_rating >= 90"
        assert _apply_prefix(sql, "") == sql

    def test_bare_column_prefix(self):
        """Test prefix applied to bare column names"""
        sql = "total_rating >= 90"
        result = _apply_prefix(sql, "g.")
        assert result == "g.total_rating >= 90"

    def test_games_dot_id_prefix(self):
        """Test games.id is replaced with prefix"""
        sql = "games.id = 1"
        result = _apply_prefix(sql, "g.")
        assert result == "g.id = 1"

    def test_games_dot_store_prefix(self):
        """Test games.store is replaced with prefix"""
        sql = "games.store = 'steam'"
        result = _apply_prefix(sql, "g.")
        assert result == "g.store = 'steam'"

    def test_games_dot_priority_prefix(self):
        """Test games.priority is replaced with prefix"""
        sql = "games.priority IS NOT NULL"
        result = _apply_prefix(sql, "g.")
        assert result == "g.priority IS NOT NULL"

    def test_games_dot_personal_rating_prefix(self):
        """Test games.personal_rating is replaced with prefix"""
        sql = "games.personal_rating > 0"
        result = _apply_prefix(sql, "g.")
        assert result == "g.personal_rating > 0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
