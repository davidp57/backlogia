# routes/api_metadata.py
# API endpoints for game metadata operations (IGDB, hidden, NSFW, etc.)

from flask import Blueprint, request, jsonify
import json

from ..database import get_db

api_metadata_bp = Blueprint('api_metadata', __name__)


@api_metadata_bp.route("/api/game/<int:game_id>/igdb", methods=["POST"])
def update_igdb(game_id):
    """Update IGDB ID for a game and resync its data."""
    # Import here to avoid circular imports
    from ..services.igdb_sync import (
        IGDBClient, extract_genres_and_themes, merge_and_dedupe_genres
    )

    data = request.get_json()
    if not data or "igdb_id" not in data:
        return jsonify({"error": "igdb_id is required"}), 400

    igdb_id = data.get("igdb_id")

    # Allow clearing the IGDB ID
    if igdb_id is None or igdb_id == "":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE games SET
                igdb_id = NULL,
                igdb_slug = NULL,
                igdb_rating = NULL,
                igdb_rating_count = NULL,
                aggregated_rating = NULL,
                aggregated_rating_count = NULL,
                total_rating = NULL,
                total_rating_count = NULL,
                igdb_summary = NULL,
                igdb_cover_url = NULL,
                igdb_screenshots = NULL,
                igdb_matched_at = NULL
            WHERE id = ?""",
            (game_id,),
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "IGDB data cleared"})

    # Validate igdb_id is a number
    try:
        igdb_id = int(igdb_id)
    except (ValueError, TypeError):
        return jsonify({"error": "igdb_id must be a number"}), 400

    # Fetch data from IGDB
    try:
        client = IGDBClient()
        igdb_game = client.get_game_by_id(igdb_id)

        if not igdb_game:
            return jsonify({"error": f"No game found with IGDB ID {igdb_id}"}), 404

        # Extract cover URL
        cover_url = None
        if igdb_game.get("cover"):
            cover_url = igdb_game["cover"].get("url", "")
            cover_url = cover_url.replace("t_thumb", "t_cover_big")
            if cover_url and not cover_url.startswith("http"):
                cover_url = "https:" + cover_url

        # Extract screenshots
        screenshots = []
        if igdb_game.get("screenshots"):
            for screenshot in igdb_game["screenshots"][:5]:
                url = screenshot.get("url", "")
                url = url.replace("t_thumb", "t_screenshot_big")
                if url and not url.startswith("http"):
                    url = "https:" + url
                screenshots.append(url)

        # Check if game is NSFW
        is_nsfw = IGDBClient.is_nsfw(igdb_game)

        # Update the database
        conn = get_db()
        cursor = conn.cursor()

        # Fetch existing genres to merge with IGDB data
        cursor.execute("SELECT genres FROM games WHERE id = ?", (game_id,))
        row = cursor.fetchone()
        existing_genres = row[0] if row else None

        # Extract genres and themes from IGDB and merge with existing
        igdb_tags = extract_genres_and_themes(igdb_game)
        merged_genres = merge_and_dedupe_genres(existing_genres, igdb_tags)

        cursor.execute(
            """UPDATE games SET
                igdb_id = ?,
                igdb_slug = ?,
                igdb_rating = ?,
                igdb_rating_count = ?,
                aggregated_rating = ?,
                aggregated_rating_count = ?,
                total_rating = ?,
                total_rating_count = ?,
                igdb_summary = ?,
                igdb_cover_url = ?,
                igdb_screenshots = ?,
                igdb_matched_at = CURRENT_TIMESTAMP,
                nsfw = ?,
                genres = ?
            WHERE id = ?""",
            (
                igdb_game.get("id"),
                igdb_game.get("slug"),
                igdb_game.get("rating"),
                igdb_game.get("rating_count"),
                igdb_game.get("aggregated_rating"),
                igdb_game.get("aggregated_rating_count"),
                igdb_game.get("total_rating"),
                igdb_game.get("total_rating_count"),
                igdb_game.get("summary"),
                cover_url,
                json.dumps(screenshots) if screenshots else None,
                1 if is_nsfw else 0,
                merged_genres,
                game_id,
            ),
        )
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Synced with IGDB: {igdb_game.get('name')}",
            "igdb_name": igdb_game.get("name"),
            "igdb_id": igdb_game.get("id")
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to fetch from IGDB: {str(e)}"}), 500


@api_metadata_bp.route("/api/game/<int:game_id>/hidden", methods=["POST"])
def update_hidden(game_id):
    """Toggle hidden status for a game."""
    data = request.get_json()
    if data is None or "hidden" not in data:
        return jsonify({"error": "hidden is required"}), 400

    hidden = 1 if data.get("hidden") else 0

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE games SET hidden = ? WHERE id = ?", (hidden, game_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "hidden": bool(hidden)})


@api_metadata_bp.route("/api/game/<int:game_id>/nsfw", methods=["POST"])
def update_nsfw(game_id):
    """Toggle NSFW status for a game."""
    data = request.get_json()
    if data is None or "nsfw" not in data:
        return jsonify({"error": "nsfw is required"}), 400

    nsfw = 1 if data.get("nsfw") else 0

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE games SET nsfw = ? WHERE id = ?", (nsfw, game_id))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "nsfw": bool(nsfw)})


@api_metadata_bp.route("/api/game/<int:game_id>/cover-override", methods=["POST"])
def update_cover_override(game_id):
    """Update the cover art override URL for a game."""
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Request body required"}), 400

    # Allow empty string or None to clear the override
    cover_url = data.get("cover_url_override", "").strip() or None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE games SET cover_url_override = ? WHERE id = ?", (cover_url, game_id)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True, "cover_url_override": cover_url})


@api_metadata_bp.route("/api/games/bulk/hide", methods=["POST"])
def bulk_hide_games():
    """Hide multiple games at once."""
    data = request.get_json()
    if data is None or "game_ids" not in data:
        return jsonify({"error": "game_ids is required"}), 400

    game_ids = data.get("game_ids", [])
    if not game_ids:
        return jsonify({"error": "No games selected"}), 400

    conn = get_db()
    cursor = conn.cursor()

    placeholders = ",".join("?" * len(game_ids))
    cursor.execute(f"UPDATE games SET hidden = 1 WHERE id IN ({placeholders})", game_ids)
    updated = cursor.rowcount

    conn.commit()
    conn.close()

    return jsonify({"success": True, "updated": updated})


@api_metadata_bp.route("/api/games/bulk/nsfw", methods=["POST"])
def bulk_nsfw_games():
    """Mark multiple games as NSFW at once."""
    data = request.get_json()
    if data is None or "game_ids" not in data:
        return jsonify({"error": "game_ids is required"}), 400

    game_ids = data.get("game_ids", [])
    if not game_ids:
        return jsonify({"error": "No games selected"}), 400

    conn = get_db()
    cursor = conn.cursor()

    placeholders = ",".join("?" * len(game_ids))
    cursor.execute(f"UPDATE games SET nsfw = 1 WHERE id IN ({placeholders})", game_ids)
    updated = cursor.rowcount

    conn.commit()
    conn.close()

    return jsonify({"success": True, "updated": updated})
