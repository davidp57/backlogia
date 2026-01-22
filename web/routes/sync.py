# routes/sync.py
# Store sync and IGDB sync routes

import sqlite3
from flask import Blueprint, jsonify

from ..config import DATABASE_PATH

sync_bp = Blueprint('sync', __name__)


@sync_bp.route("/api/sync/store/<store>", methods=["POST"])
def sync_store(store):
    """Sync games from a specific store or all stores."""
    # Import here to avoid circular imports
    from ..services.database_builder import (
        create_database, import_steam_games, import_epic_games,
        import_gog_games, import_itch_games, import_humble_games,
        import_battlenet_games, import_amazon_games
    )

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        # Ensure database tables exist
        create_database()
        conn = sqlite3.connect(DATABASE_PATH)

        results = {}

        if store == "steam" or store == "all":
            results["steam"] = import_steam_games(conn)

        if store == "epic" or store == "all":
            results["epic"] = import_epic_games(conn)

        if store == "gog" or store == "all":
            results["gog"] = import_gog_games(conn)

        if store == "itch" or store == "all":
            results["itch"] = import_itch_games(conn)

        if store == "humble" or store == "all":
            results["humble"] = import_humble_games(conn)

        if store == "battlenet" or store == "all":
            results["battlenet"] = import_battlenet_games(conn)

        if store == "amazon" or store == "all":
            results["amazon"] = import_amazon_games(conn)

        conn.close()

        if store == "all":
            total = sum(results.values())
            message = f"Synced {total} games: " + ", ".join(
                f"{s.capitalize()}: {c}" for s, c in results.items()
            )
        else:
            count = results.get(store, 0)
            message = f"Synced {count} games from {store.capitalize()}"

        return jsonify({"success": True, "message": message, "results": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@sync_bp.route("/api/sync/igdb/<mode>", methods=["POST"])
def sync_igdb(mode):
    """Sync IGDB metadata for games."""
    # Import here to avoid circular imports
    from ..services.igdb_sync import IGDBClient, sync_games as igdb_sync_games, add_igdb_columns

    try:
        conn = sqlite3.connect(DATABASE_PATH)

        # Ensure IGDB columns exist
        add_igdb_columns(conn)

        # Initialize client
        client = IGDBClient()

        # Sync games (force=True for 'all' mode)
        force = (mode == "all")
        matched, failed = igdb_sync_games(conn, client, force=force)

        conn.close()

        message = f"IGDB sync complete: {matched} matched, {failed} failed/no match"
        return jsonify({"success": True, "message": message, "matched": matched, "failed": failed})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
