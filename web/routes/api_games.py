# routes/api_games.py
# API endpoints for games data

from flask import Blueprint, jsonify

from ..database import get_db
from ..utils.filters import EXCLUDE_DUPLICATES_FILTER

api_games_bp = Blueprint('api_games', __name__)


@api_games_bp.route("/api/games")
def api_games():
    """API endpoint for games."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM games WHERE 1=1" + EXCLUDE_DUPLICATES_FILTER + " ORDER BY name")
    games = cursor.fetchall()

    conn.close()

    return jsonify([dict(g) for g in games])


@api_games_bp.route("/api/stats")
def api_stats():
    """API endpoint for library statistics."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM games WHERE 1=1" + EXCLUDE_DUPLICATES_FILTER)
    total = cursor.fetchone()[0]

    cursor.execute("SELECT store, COUNT(*) FROM games WHERE 1=1" + EXCLUDE_DUPLICATES_FILTER + " GROUP BY store")
    by_store = dict(cursor.fetchall())

    cursor.execute("SELECT SUM(playtime_hours) FROM games WHERE playtime_hours IS NOT NULL" + EXCLUDE_DUPLICATES_FILTER)
    total_playtime = cursor.fetchone()[0] or 0

    conn.close()

    return jsonify({
        "total_games": total,
        "by_store": by_store,
        "total_playtime_hours": round(total_playtime, 1)
    })
