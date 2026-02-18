# helpers.py
# Utility functions for the Backlogia application

import json
from urllib.parse import quote
from .filters import PREDEFINED_QUERIES, EXCLUDE_HIDDEN_FILTER


def parse_json_field(value):
    """Safely parse a JSON field."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def get_store_url(store, store_id, extra_data=None):
    """Generate the store URL for a game."""
    if not store_id:
        return None

    if store == "steam":
        return f"https://store.steampowered.com/app/{store_id}"
    elif store == "epic":
        # Try to use the product slug from extra_data (extracted from Epic metadata)
        if extra_data:
            try:
                data = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                product_slug = data.get("product_slug")
                if product_slug:
                    return f"https://store.epicgames.com/en-US/p/{product_slug}"
                # Fallback: search the Epic Store by game name
                name = data.get("name")
                if name:
                    return f"https://store.epicgames.com/en-US/browse?q={quote(name)}&sortBy=relevancy"
            except (json.JSONDecodeError, TypeError):
                pass
        return None
    elif store == "gog":
        # GOG URLs use the product ID
        return f"https://www.gog.com/en/game/{store_id}"
    elif store == "itch":
        # Itch URLs are stored in extra_data
        if extra_data:
            try:
                data = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                return data.get("url")
            except (json.JSONDecodeError, TypeError):
                pass
        return None
    elif store == "humble":
        # Humble Bundle URLs - link to downloads page with gamekey
        if extra_data:
            try:
                data = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                gamekey = data.get("gamekey")
                if gamekey:
                    return f"https://www.humblebundle.com/downloads?key={gamekey}"
            except (json.JSONDecodeError, TypeError):
                pass
        return None
    elif store == "battlenet":
        # Battle.net - link to account games page
        return "https://account.battle.net/games"
    elif store == "amazon":
        # Amazon Games - link to game library
        return "https://gaming.amazon.com/home"
    elif store == "xbox":
        # Xbox Store URL
        if store_id:
            return f"https://www.xbox.com/games/store/game/{store_id}"
        return None
    return None


def group_games_by_igdb(games):
    """Group games by IGDB ID, keeping separate entries for games without IGDB match."""
    grouped = {}
    no_igdb_games = []

    for game in games:
        game_dict = dict(game)
        igdb_id = game_dict.get("igdb_id")

        # Check if this game has is_streaming flag in extra_data
        is_streaming = False
        extra_data = game_dict.get("extra_data")
        if extra_data:
            try:
                data = json.loads(extra_data) if isinstance(extra_data, str) else extra_data
                is_streaming = data.get("is_streaming", False)
            except (json.JSONDecodeError, TypeError):
                pass

        has_non_streaming = not is_streaming

        if igdb_id:
            if igdb_id not in grouped:
                grouped[igdb_id] = {
                    "primary": game_dict,
                    "stores": [game_dict["store"]],
                    "game_ids": [game_dict["id"]],
                    "store_data": {game_dict["store"]: game_dict},
                    "is_streaming": is_streaming,
                    "has_non_streaming": has_non_streaming
                }
            else:
                grouped[igdb_id]["stores"].append(game_dict["store"])
                grouped[igdb_id]["game_ids"].append(game_dict["id"])
                grouped[igdb_id]["store_data"][game_dict["store"]] = game_dict
                # Aggregate streaming flag - if any game has it, the group has it
                if is_streaming:
                    grouped[igdb_id]["is_streaming"] = True
                # Track if any copy is non-streaming (owned)
                if has_non_streaming:
                    grouped[igdb_id]["has_non_streaming"] = True
                # Use the one with more data as primary (prefer one with playtime or better cover)
                current_primary = grouped[igdb_id]["primary"]
                if (game_dict.get("playtime_hours") and not current_primary.get("playtime_hours")) or \
                   (game_dict.get("igdb_cover_url") and not current_primary.get("igdb_cover_url")):
                    grouped[igdb_id]["primary"] = game_dict
        else:
            no_igdb_games.append({
                "primary": game_dict,
                "stores": [game_dict["store"]],
                "game_ids": [game_dict["id"]],
                "store_data": {game_dict["store"]: game_dict},
                "is_streaming": is_streaming,
                "has_non_streaming": has_non_streaming
            })

    # Convert grouped dict to list and add non-IGDB games
    result = list(grouped.values()) + no_igdb_games

    # Set only_streaming flag: True if game is streaming and has no non-streaming copies
    for game in result:
        game["only_streaming"] = game.get("is_streaming", False) and not game.get("has_non_streaming", False)

    return result


def get_query_filter_counts(cursor, stores=None, genres=None, exclude_query=None):
    """
    Calculate the number of games that match each predefined query filter.
    
    Args:
        cursor: Database cursor
        stores: List of stores to filter by (optional)
        genres: List of genres to filter by (optional)
        exclude_query: Query filter ID to exclude from the WHERE clause (optional)
    
    Returns:
        Dict mapping query filter IDs to their result counts
    """
    # Build base WHERE clause with store and genre filters
    # Start with EXCLUDE_HIDDEN_FILTER which already has "AND" prefix
    where_conditions = ["1=1" + EXCLUDE_HIDDEN_FILTER]
    params = []
    
    if stores:
        placeholders = ','.join(['?' for _ in stores])
        where_conditions.append(f"store IN ({placeholders})")
        params.extend(stores)
    
    if genres:
        # For genres, we need to check if the genre appears in the JSON array
        genre_conditions = []
        for genre in genres:
            genre_conditions.append("genres LIKE ?")
            params.append(f'%"{genre}"%')
        where_conditions.append(f"({' OR '.join(genre_conditions)})")
    
    base_where = " AND ".join(where_conditions)
    
    # Build a single SQL query with COUNT(CASE) for all filters
    # Use indexed approach since filter IDs contain hyphens (not valid in SQL)
    count_cases = []
    filter_ids = []
    for filter_id, condition in PREDEFINED_QUERIES.items():
        if filter_id == exclude_query:
            continue  # Skip the filter we're currently viewing
        count_cases.append(f"COUNT(CASE WHEN {condition} THEN 1 END)")
        filter_ids.append(filter_id)
    
    query = f"""
        SELECT {', '.join(count_cases)}
        FROM games
        WHERE {base_where}
    """
    
    cursor.execute(query, params)
    row = cursor.fetchone()
    
    # Convert row to dictionary
    counts = {}
    if row:
        for i, filter_id in enumerate(filter_ids):
            counts[filter_id] = row[i]
    
    return counts
