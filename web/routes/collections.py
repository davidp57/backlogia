# routes/collections.py
# Collections page and API routes

from flask import Blueprint, render_template, request, jsonify

from ..database import get_db
from ..utils.helpers import parse_json_field, group_games_by_igdb

collections_bp = Blueprint('collections', __name__)


@collections_bp.route("/collections")
def collections_page():
    """Collections listing page."""
    conn = get_db()
    cursor = conn.cursor()

    # Get all collections with game count and cover thumbnails
    cursor.execute("""
        SELECT
            c.id,
            c.name,
            c.description,
            c.created_at,
            COUNT(cg.game_id) as game_count
        FROM collections c
        LEFT JOIN collection_games cg ON c.id = cg.collection_id
        GROUP BY c.id
        ORDER BY c.updated_at DESC
    """)
    collections = cursor.fetchall()

    # Get cover images for each collection (up to 4 games)
    collections_with_covers = []
    for collection in collections:
        collection_dict = dict(collection)
        cursor.execute("""
            SELECT g.igdb_cover_url, g.cover_image
            FROM collection_games cg
            JOIN games g ON cg.game_id = g.id
            WHERE cg.collection_id = ?
            ORDER BY cg.added_at DESC
            LIMIT 4
        """, (collection_dict["id"],))
        covers = []
        for row in cursor.fetchall():
            cover = row["igdb_cover_url"] or row["cover_image"]
            if cover:
                covers.append(cover)
        collection_dict["covers"] = covers
        collections_with_covers.append(collection_dict)

    conn.close()

    return render_template(
        "collections.html",
        collections=collections_with_covers
    )


@collections_bp.route("/collection/<int:collection_id>")
def collection_detail(collection_id):
    """View a single collection with its games."""
    conn = get_db()
    cursor = conn.cursor()

    # Get collection info
    cursor.execute("SELECT * FROM collections WHERE id = ?", (collection_id,))
    collection = cursor.fetchone()

    if not collection:
        conn.close()
        return "Collection not found", 404

    # Get games in collection
    cursor.execute("""
        SELECT g.*, cg.added_at as collection_added_at
        FROM collection_games cg
        JOIN games g ON cg.game_id = g.id
        WHERE cg.collection_id = ?
        ORDER BY cg.added_at DESC
    """, (collection_id,))
    games = cursor.fetchall()

    # Group games by IGDB ID (like the library page)
    grouped_games = group_games_by_igdb(games)

    conn.close()

    return render_template(
        "collection_detail.html",
        collection=dict(collection),
        games=grouped_games,
        parse_json=parse_json_field
    )


@collections_bp.route("/api/collections", methods=["GET"])
def api_get_collections():
    """Get all collections."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.name, c.description, COUNT(cg.game_id) as game_count
        FROM collections c
        LEFT JOIN collection_games cg ON c.id = cg.collection_id
        GROUP BY c.id
        ORDER BY c.name
    """)
    collections = [dict(c) for c in cursor.fetchall()]

    conn.close()
    return jsonify(collections)


@collections_bp.route("/api/collections", methods=["POST"])
def api_create_collection():
    """Create a new collection."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    name = data.get("name").strip()
    description = data.get("description", "").strip() or None

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO collections (name, description) VALUES (?, ?)",
        (name, description)
    )
    collection_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "id": collection_id,
        "name": name,
        "description": description
    })


@collections_bp.route("/api/collections/<int:collection_id>", methods=["DELETE"])
def api_delete_collection(collection_id):
    """Delete a collection."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Collection not found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@collections_bp.route("/api/collections/<int:collection_id>", methods=["PUT"])
def api_update_collection(collection_id):
    """Update a collection's name and description."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check if collection exists
    cursor.execute("SELECT id FROM collections WHERE id = ?", (collection_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Collection not found"}), 404

    # Build update query
    updates = []
    params = []

    if "name" in data:
        updates.append("name = ?")
        params.append(data["name"].strip())

    if "description" in data:
        updates.append("description = ?")
        params.append(data["description"].strip() or None)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(collection_id)
        cursor.execute(
            f"UPDATE collections SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()

    conn.close()
    return jsonify({"success": True})


@collections_bp.route("/api/collections/<int:collection_id>/games", methods=["POST"])
def api_add_game_to_collection(collection_id):
    """Add a game to a collection."""
    data = request.get_json()
    if not data or "game_id" not in data:
        return jsonify({"error": "game_id is required"}), 400

    game_id = data.get("game_id")

    conn = get_db()
    cursor = conn.cursor()

    # Check if collection exists
    cursor.execute("SELECT id FROM collections WHERE id = ?", (collection_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Collection not found"}), 404

    # Check if game exists
    cursor.execute("SELECT id FROM games WHERE id = ?", (game_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Game not found"}), 404

    # Try to add (ignore if already exists)
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO collection_games (collection_id, game_id) VALUES (?, ?)",
            (collection_id, game_id)
        )
        # Update collection's updated_at
        cursor.execute(
            "UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (collection_id,)
        )
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

    conn.close()
    return jsonify({"success": True})


@collections_bp.route("/api/collections/<int:collection_id>/games/<int:game_id>", methods=["DELETE"])
def api_remove_game_from_collection(collection_id, game_id):
    """Remove a game from a collection."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM collection_games WHERE collection_id = ? AND game_id = ?",
        (collection_id, game_id)
    )

    if cursor.rowcount == 0:
        conn.close()
        return jsonify({"error": "Game not in collection"}), 404

    # Update collection's updated_at
    cursor.execute(
        "UPDATE collections SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (collection_id,)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})


@collections_bp.route("/api/game/<int:game_id>/collections", methods=["GET"])
def api_get_game_collections(game_id):
    """Get all collections a game belongs to."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.id, c.name
        FROM collections c
        JOIN collection_games cg ON c.id = cg.collection_id
        WHERE cg.game_id = ?
        ORDER BY c.name
    """, (game_id,))

    collections = [dict(c) for c in cursor.fetchall()]
    conn.close()

    return jsonify(collections)
