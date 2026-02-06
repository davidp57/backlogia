# routes/api_games.py
# API endpoints for games data

import sqlite3

from fastapi import APIRouter, Depends

from ..dependencies import get_db
from ..utils.filters import EXCLUDE_DUPLICATES_FILTER

router = APIRouter(tags=["Games"])


@router.get("/api/games")
def api_games(conn: sqlite3.Connection = Depends(get_db)):
    """Get all games in the library."""
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM games WHERE 1=1" + EXCLUDE_DUPLICATES_FILTER + " ORDER BY name")
    games = cursor.fetchall()

    return [dict(g) for g in games]


@router.get("/api/stats")
def api_stats(conn: sqlite3.Connection = Depends(get_db)):
    """Get library statistics."""
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM games WHERE 1=1" + EXCLUDE_DUPLICATES_FILTER)
    total = cursor.fetchone()[0]

    cursor.execute("SELECT store, COUNT(*) FROM games WHERE 1=1" + EXCLUDE_DUPLICATES_FILTER + " GROUP BY store")
    by_store = dict(cursor.fetchall())

    cursor.execute("SELECT SUM(playtime_hours) FROM games WHERE playtime_hours IS NOT NULL" + EXCLUDE_DUPLICATES_FILTER)
    total_playtime = cursor.fetchone()[0] or 0

    return {
        "total_games": total,
        "by_store": by_store,
        "total_playtime_hours": round(total_playtime, 1)
    }


@router.get("/api/game/{game_id}/news")
def api_game_news(game_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Get news articles for a specific game."""
    from fastapi import HTTPException
    
    cursor = conn.cursor()
    
    # Check if game exists
    cursor.execute("SELECT id, name, store FROM games WHERE id = ?", (game_id,))
    game = cursor.fetchone()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Only Steam games have news
    if game['store'] != 'steam':
        return {
            "game_id": game_id,
            "game_name": game['name'],
            "articles": [],
            "message": "News is only available for Steam games"
        }
    
    # Fetch news articles (newest first)
    cursor.execute("""
        SELECT title, content, author, url, published_at, fetched_at
        FROM game_news
        WHERE game_id = ?
        ORDER BY published_at DESC
    """, (game_id,))
    
    articles = [dict(row) for row in cursor.fetchall()]
    
    return {
        "game_id": game_id,
        "game_name": game['name'],
        "articles": articles,
        "count": len(articles)
    }


@router.get("/api/game/{game_id}/updates")
def api_game_updates(game_id: int, limit: int = 10, conn: sqlite3.Connection = Depends(get_db)):
    """Get depot update history for a specific game."""
    from fastapi import HTTPException
    
    cursor = conn.cursor()
    
    # Check if game exists
    cursor.execute("SELECT id, name, store, last_modified FROM games WHERE id = ?", (game_id,))
    game = cursor.fetchone()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Fetch update history (newest first)
    cursor.execute("""
        SELECT depot_id, manifest_id, update_timestamp, fetched_at
        FROM game_depot_updates
        WHERE game_id = ?
        ORDER BY update_timestamp DESC
        LIMIT ?
    """, (game_id, limit))
    
    updates = [dict(row) for row in cursor.fetchall()]
    
    return {
        "game_id": game_id,
        "game_name": game['name'],
        "store": game['store'],
        "last_modified": game['last_modified'],
        "updates": updates,
        "count": len(updates)
    }

