# helpers.py
# Utility functions for the Backlogia application

import json


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
        # Epic URLs use the app_name slug
        return f"https://store.epicgames.com/en-US/p/{store_id}"
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
    return None


def group_games_by_igdb(games):
    """Group games by IGDB ID, keeping separate entries for games without IGDB match."""
    grouped = {}
    no_igdb_games = []

    for game in games:
        game_dict = dict(game)
        igdb_id = game_dict.get("igdb_id")

        if igdb_id:
            if igdb_id not in grouped:
                grouped[igdb_id] = {
                    "primary": game_dict,
                    "stores": [game_dict["store"]],
                    "game_ids": [game_dict["id"]],
                    "store_data": {game_dict["store"]: game_dict}
                }
            else:
                grouped[igdb_id]["stores"].append(game_dict["store"])
                grouped[igdb_id]["game_ids"].append(game_dict["id"])
                grouped[igdb_id]["store_data"][game_dict["store"]] = game_dict
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
                "store_data": {game_dict["store"]: game_dict}
            })

    # Convert grouped dict to list and add non-IGDB games
    result = list(grouped.values()) + no_igdb_games
    return result
