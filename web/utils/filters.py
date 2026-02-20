# filters.py
# SQL filter constants for game queries

# Filter out duplicate GOG entries from Amazon Prime/Luna
EXCLUDE_DUPLICATES_FILTER = """
    AND name NOT LIKE '% - Amazon Prime'
    AND name NOT LIKE '% - Amazon Luna'
"""

# Filter to exclude hidden games (in addition to duplicates)
EXCLUDE_HIDDEN_FILTER = EXCLUDE_DUPLICATES_FILTER + """
    AND (hidden IS NULL OR hidden = 0)
"""

# Subquery template for system tag matching
_TAG_EXISTS = """EXISTS (
    SELECT 1 FROM game_labels _gl JOIN labels _l ON _l.id = _gl.label_id
    WHERE _gl.game_id = games.id AND _l.system = 1 AND _l.type = 'system_tag'
    AND _l.name = '{tag_name}'
)"""

_TAG_NOT_EXISTS_EXCEPT = """NOT EXISTS (
    SELECT 1 FROM game_labels _gl JOIN labels _l ON _l.id = _gl.label_id
    WHERE _gl.game_id = games.id AND _l.system = 1 AND _l.type = 'system_tag'
    AND _l.name != '{except_tag}'
)"""

_TAG_NOT_EXISTS = """NOT EXISTS (
    SELECT 1 FROM game_labels _gl JOIN labels _l ON _l.id = _gl.label_id
    WHERE _gl.game_id = games.id AND _l.system = 1 AND _l.type = 'system_tag'
)"""

# Predefined query filters
PREDEFINED_QUERIES = {
    # Gameplay (tag-based)
    "unplayed": """(
    (games.store = 'steam' AND """ + _TAG_NOT_EXISTS_EXCEPT.format(except_tag='Never Launched') + """)
    OR
    (games.store != 'steam' AND """ + _TAG_NOT_EXISTS + """)
)""",
    "just-tried": _TAG_EXISTS.format(tag_name='Just Tried'),
    "played": _TAG_EXISTS.format(tag_name='Played'),
    "well-played": _TAG_EXISTS.format(tag_name='Well Played'),
    "heavily-played": _TAG_EXISTS.format(tag_name='Heavily Played'),

    # Ratings
    "highly-rated": "total_rating >= 90",
    "well-rated": "total_rating >= 75",
    "below-average": "(total_rating < 75 AND total_rating IS NOT NULL)",
    "unrated": "total_rating IS NULL",
    "hidden-gems": "(total_rating >= 75 AND total_rating < 90 AND aggregated_rating IS NULL)",
    "critic-favorites": "aggregated_rating >= 80",
    "community-favorites": "(igdb_rating >= 85 AND igdb_rating_count >= 100)",

    # Dates
    "recently-added": "added_at >= DATE('now', '-30 days')",
    "older-library": "added_at < DATE('now', '-6 months')",
    "recent-releases": "release_date >= DATE('now', '-1 year')",
    "recently-updated": "last_modified >= DATE('now', '-30 days')",
    "classics": "(release_date <= DATE('now', '-10 years') AND total_rating >= 80)",

    # Content
    "nsfw": "nsfw = 1",
    "safe": "(nsfw = 0 OR nsfw IS NULL)",

    # My Rating
    "has-priority": "games.priority IS NOT NULL",
    "no-priority": "games.priority IS NULL",
    "personally-rated": "(games.personal_rating IS NOT NULL AND games.personal_rating > 0)",
    "personally-unrated": "(games.personal_rating IS NULL OR games.personal_rating = 0)",
}

# Display names for UI
QUERY_DISPLAY_NAMES = {
    "unplayed": "Unplayed",
    "just-tried": "Just Tried",
    "played": "Played",
    "well-played": "Well Played",
    "heavily-played": "Heavily Played",
    "highly-rated": "Highly Rated",
    "well-rated": "Well Rated",
    "below-average": "Below Average",
    "unrated": "Unrated",
    "hidden-gems": "Hidden Gems",
    "critic-favorites": "Critic Favorites",
    "community-favorites": "Community Favorites",
    "recently-added": "Recently Added",
    "older-library": "Older Library",
    "recent-releases": "Recent Releases",
    "recently-updated": "Recently Updated (Epic only)",
    "classics": "Classics",
    "nsfw": "NSFW",
    "safe": "Safe Content",
    "has-priority": "Has Priority",
    "no-priority": "No Priority",
    "personally-rated": "Personally Rated",
    "personally-unrated": "Personally Unrated",
}

# Category grouping for UI organization
QUERY_CATEGORIES = {
    "Gameplay": ["unplayed", "just-tried", "played", "well-played", "heavily-played"],
    "Ratings": ["highly-rated", "well-rated", "below-average", "unrated", "hidden-gems",
                "critic-favorites", "community-favorites"],
    "Dates": ["recently-added", "older-library", "recent-releases", "recently-updated", "classics"],
    "Content": ["nsfw", "safe"],
    "My Rating": ["has-priority", "no-priority", "personally-rated", "personally-unrated"],
}

# Filter descriptions for tooltips
QUERY_DESCRIPTIONS = {
    "unplayed": "Games with no gameplay tag (Steam: no tag other than Never Launched)",
    "just-tried": "Games tagged as Just Tried",
    "played": "Games tagged as Played",
    "well-played": "Games tagged as Well Played",
    "heavily-played": "Games tagged as Heavily Played",
    "highly-rated": "Games rated 90 or higher",
    "well-rated": "Games rated 75 or higher",
    "below-average": "Games rated below 75",
    "unrated": "Games without rating data",
    "hidden-gems": "Well-rated games (75-89) without critic reviews",
    "critic-favorites": "Games with critic score 80+",
    "community-favorites": "Games with high user ratings (85+) and 100+ votes",
    "recently-added": "Games added in the last 30 days",
    "older-library": "Games added 6+ months ago",
    "recent-releases": "Games released in the last year",
    "recently-updated": "Games updated in the last 30 days (Epic only)",
    "classics": "Games released 10+ years ago with 80+ rating",
    "nsfw": "Adult content games",
    "safe": "Non-adult content games",
    "has-priority": "Games with a priority set",
    "no-priority": "Games without a priority",
    "personally-rated": "Games you have rated",
    "personally-unrated": "Games you haven't rated yet",
}

# Bare column names that need prefix replacement for collection queries
# Note: priority and personal_rating are always written as games.X in filters,
# so they're handled by the explicit games.X replacements in _apply_prefix
_PREFIXABLE_COLUMNS = [
    'playtime_hours', 'total_rating', 'added_at', 'release_date',
    'nsfw', 'aggregated_rating', 'igdb_rating', 'igdb_rating_count',
    'last_modified',
]


def _apply_prefix(sql, table_prefix):
    """Apply table prefix to column names and table references in SQL."""
    if not table_prefix:
        return sql
    # Replace explicit table references first
    sql = sql.replace("games.id", f"{table_prefix}id")
    sql = sql.replace("games.store", f"{table_prefix}store")
    sql = sql.replace("games.priority", f"{table_prefix}priority")
    sql = sql.replace("games.personal_rating", f"{table_prefix}personal_rating")
    # Replace bare column names
    for col in _PREFIXABLE_COLUMNS:
        sql = sql.replace(col, f'{table_prefix}{col}')
    return sql


def build_query_filter_sql(query_ids, table_prefix=""):
    """
    Build SQL filter condition from query IDs with proper OR/AND logic.

    Filters within the same category are combined with OR.
    Filters from different categories are combined with AND.

    Args:
        query_ids: List of query filter IDs (e.g., ['played', 'just-tried', 'highly-rated'])
        table_prefix: Optional table prefix for column names (e.g., 'g.' for joins)

    Returns:
        SQL condition string, or empty string if no valid queries

    Example:
        ['played', 'just-tried', 'highly-rated'] →
        "((EXISTS ...) OR (EXISTS ...)) AND (total_rating >= 90))"
    """
    if not query_ids:
        return ""

    # Filter valid queries
    valid_queries = [q for q in query_ids if q in PREDEFINED_QUERIES]
    if not valid_queries:
        return ""

    # Group queries by category
    category_groups = {}
    for query_id in valid_queries:
        # Find which category this query belongs to
        category_found = None
        for category, filter_ids in QUERY_CATEGORIES.items():
            if query_id in filter_ids:
                category_found = category
                break

        if category_found:
            if category_found not in category_groups:
                category_groups[category_found] = []
            category_groups[category_found].append(query_id)

    # Build SQL conditions
    category_conditions = []
    for category, query_list in category_groups.items():
        if len(query_list) == 1:
            sql = _apply_prefix(PREDEFINED_QUERIES[query_list[0]], table_prefix)
            category_conditions.append(f"({sql})")
        else:
            # Multiple queries in same category - combine with OR
            query_sqls = []
            for query_id in query_list:
                sql = _apply_prefix(PREDEFINED_QUERIES[query_id], table_prefix)
                query_sqls.append(f"({sql})")
            category_conditions.append(f"({' OR '.join(query_sqls)})")

    # Combine categories with AND
    if len(category_conditions) == 1:
        return category_conditions[0]
    else:
        return "(" + " AND ".join(category_conditions) + ")"
