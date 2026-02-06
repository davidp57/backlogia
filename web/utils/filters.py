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

# Predefined query filters
PREDEFINED_QUERIES = {
    # Gameplay
    "unplayed": "(playtime_hours IS NULL OR playtime_hours = 0)",
    "played": "playtime_hours > 0",
    "started": "(playtime_hours > 0 AND playtime_hours < 5)",
    "well-played": "playtime_hours >= 5",
    "heavily-played": "playtime_hours >= 20",
    
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
    "recent-updates-detected": "id IN (SELECT game_id FROM game_depot_updates WHERE update_timestamp >= datetime('now', '-30 days'))",
    "classics": "(release_date <= DATE('now', '-10 years') AND total_rating >= 80)",
    
    # Development Status
    "early-access": "development_status = 'early_access'",
    "leaving-early-access": "(development_status = 'early_access' AND last_modified >= DATE('now', '-90 days'))",
    "in-development": "development_status IN ('alpha', 'beta', 'early_access')",
    "released": "development_status = 'released'",
    
    # Content
    "nsfw": "nsfw = 1",
    "safe": "(nsfw = 0 OR nsfw IS NULL)"
}

# Display names for UI
QUERY_DISPLAY_NAMES = {
    "unplayed": "Unplayed",
    "played": "Played",
    "started": "Started",
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
    "recently-updated": "Recently Updated",
    "recent-updates-detected": "Recent Updates",
    "classics": "Classics",
    "early-access": "Early Access",
    "leaving-early-access": "Leaving Early Access",
    "in-development": "In Development",
    "released": "Released",
    "nsfw": "NSFW",
    "safe": "Safe Content"
}

# Category grouping for UI organization
QUERY_CATEGORIES = {
    "Gameplay": ["unplayed", "played", "started", "well-played", "heavily-played"],
    "Ratings": ["highly-rated", "well-rated", "below-average", "unrated", "hidden-gems", 
                "critic-favorites", "community-favorites"],
    "Dates": ["recently-added", "older-library", "recent-releases", "recently-updated", "recent-updates-detected", "classics"],
    "Development Status": ["early-access", "leaving-early-access", "in-development", "released"],
    "Content": ["nsfw", "safe"]
}

# Filter descriptions for tooltips
QUERY_DESCRIPTIONS = {
    "unplayed": "Games with 0 hours played",
    "played": "Games with any playtime",
    "started": "Games played less than 5 hours",
    "well-played": "Games played 5+ hours",
    "heavily-played": "Games played 20+ hours",
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
    "recently-updated": "Games updated in the last 30 days",
    "recent-updates-detected": "Games with detected version updates in the last 30 days",
    "classics": "Games released 10+ years ago with 80+ rating",
    "early-access": "Games in Early Access",
    "leaving-early-access": "Early Access games updated in the last 90 days (may be near release)",
    "in-development": "Games in Alpha, Beta, or Early Access",
    "released": "Fully released games",
    "nsfw": "Adult content games",
    "safe": "Non-adult content games"
}
