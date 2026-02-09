# routes/collections.py
# Collections page and API routes

import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..dependencies import get_db
from ..utils.helpers import parse_json_field, group_games_by_igdb
from ..utils.filters import build_query_filter_sql

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


class CreateCollectionRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateCollectionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AddGameRequest(BaseModel):
    game_id: int


@router.get("/collections", response_class=HTMLResponse)
def collections_page(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    """Collections listing page."""
    cursor = conn.cursor()

    # Get all collections with game count and cover thumbnails
    cursor.execute("""
        SELECT
            l.id,
            l.name,
            l.description,
            l.created_at,
            COUNT(gl.game_id) as game_count
        FROM labels l
        LEFT JOIN game_labels gl ON l.id = gl.label_id
        WHERE l.type = 'collection'
        GROUP BY l.id
        ORDER BY l.updated_at DESC
    """)
    collections = cursor.fetchall()

    # Get cover images for each collection (up to 4 games)
    collections_with_covers = []
    for collection in collections:
        collection_dict = dict(collection)
        cursor.execute("""
            SELECT g.igdb_cover_url, g.cover_image
            FROM game_labels gl
            JOIN games g ON gl.game_id = g.id
            WHERE gl.label_id = ?
            ORDER BY gl.added_at DESC
            LIMIT 4
        """, (collection_dict["id"],))
        covers = []
        for row in cursor.fetchall():
            cover = row["igdb_cover_url"] or row["cover_image"]
            if cover:
                covers.append(cover)
        collection_dict["covers"] = covers
        collections_with_covers.append(collection_dict)

    return templates.TemplateResponse(
        request,
        "collections.html",
        {
            "collections": collections_with_covers
        }
    )


@router.get("/collection/{label_id}", response_class=HTMLResponse)
def collection_detail(
    request: Request,
    label_id: int,
    stores: list[str] = Query(default=[]),
    genres: list[str] = Query(default=[]),
    queries: list[str] = Query(default=[]),
    conn: sqlite3.Connection = Depends(get_db)
):
    """View a single collection with its games (with optional filters)."""
    from ..utils.filters import QUERY_DISPLAY_NAMES, QUERY_CATEGORIES, QUERY_DESCRIPTIONS
    
    cursor = conn.cursor()

    # Get collection info
    cursor.execute("SELECT * FROM labels WHERE type = 'collection' AND id = ?", (label_id,))
    collection = cursor.fetchone()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Get store and genre counts for filters (from all collection games, not filtered)
    cursor.execute("""
        SELECT g.store, COUNT(*) as count
        FROM game_labels gl
        JOIN games g ON gl.game_id = g.id
        WHERE gl.label_id = ?
        GROUP BY g.store
        ORDER BY count DESC
    """, (label_id,))
    store_counts = dict(cursor.fetchall())
    
    cursor.execute("""
        SELECT DISTINCT g.genres
        FROM game_labels gl
        JOIN games g ON gl.game_id = g.id
        WHERE gl.label_id = ? AND g.genres IS NOT NULL AND g.genres != '[]'
    """, (label_id,))
    genre_counts = {}
    for row in cursor.fetchall():
        try:
            genres_list = json.loads(row[0])
            for genre in genres_list:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    genre_counts = dict(sorted(genre_counts.items(), key=lambda x: x[1], reverse=True))

    # Build query with filters
    query = """
        SELECT g.*, gl.added_at as collection_added_at
        FROM game_labels gl
        JOIN games g ON gl.game_id = g.id
        WHERE gl.label_id = ?
    """
    params: list[str | int] = [label_id]

    if stores:
        placeholders = ",".join("?" * len(stores))
        query += f" AND g.store IN ({placeholders})"
        params.extend(stores)

    if genres:
        genre_conditions = []
        for genre in genres:
            genre_conditions.append("LOWER(g.genres) LIKE ?")
            params.append(f'%"{genre.lower()}"%')
        query += " AND (" + " OR ".join(genre_conditions) + ")"
    
    if queries:
        filter_sql = build_query_filter_sql(queries, table_prefix="g.")
        if filter_sql:
            query += f" AND {filter_sql}"

    query += " ORDER BY gl.added_at DESC"
    cursor.execute(query, params)
    games = cursor.fetchall()

    # Group games by IGDB ID (like the library page)
    grouped_games = group_games_by_igdb(games)

    # Calculate query_filter_counts like in library.py
    from ..utils.helpers import get_query_filter_counts
    query_filter_counts = {}
    if grouped_games:
        query_filter_counts = get_query_filter_counts(cursor)

    return templates.TemplateResponse(
        request,
        "collection_detail.html",
        {
            "collection": dict(collection),
            "games": grouped_games,
            "parse_json": parse_json_field,
            # Filter data for _filter_bar.html
            "store_counts": store_counts,
            "genre_counts": genre_counts,
            "current_stores": stores,
            "current_genres": genres,
            "current_queries": queries,
            "query_display_names": QUERY_DISPLAY_NAMES,
            "query_categories": QUERY_CATEGORIES,
            "query_descriptions": QUERY_DESCRIPTIONS,
            "query_filter_counts": query_filter_counts,
            "show_search": False,  # No search on collection detail
            "show_sort": False,  # No sort on collection detail
            "show_actions": True,
        }
    )


@router.get("/api/collections", tags=["Collections"])
def api_get_collections(conn: sqlite3.Connection = Depends(get_db)):
    """Get all collections."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.id, l.name, l.description, COUNT(gl.game_id) as game_count
        FROM labels l
        LEFT JOIN game_labels gl ON l.id = gl.label_id
        WHERE l.type = 'collection'
        GROUP BY l.id
        ORDER BY l.name
    """)
    collections = [dict(c) for c in cursor.fetchall()]

    return collections


@router.post("/api/collections", tags=["Collections"])
def api_create_collection(body: CreateCollectionRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Create a new collection."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    description = body.description.strip() if body.description else None

    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO labels (name, type, description) VALUES (?, 'collection', ?)",
        (name, description)
    )
    label_id = cursor.lastrowid
    conn.commit()

    return {
        "success": True,
        "id": label_id,
        "name": name,
        "description": description
    }


@router.delete("/api/collections/{label_id}", tags=["Collections"])
def api_delete_collection(label_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Delete a collection."""
    cursor = conn.cursor()

    cursor.execute("DELETE FROM labels WHERE type = 'collection' AND id = ?", (label_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Collection not found")

    conn.commit()

    return {"success": True}


@router.put("/api/collections/{label_id}", tags=["Collections"])
def api_update_collection(label_id: int, body: UpdateCollectionRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Update a collection's name and description."""
    cursor = conn.cursor()

    # Check if collection exists
    cursor.execute("SELECT id FROM labels WHERE type = 'collection' AND id = ?", (label_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Collection not found")

    # Build update query
    updates = []
    params: list[str | int | None] = []

    if body.name is not None:
        updates.append("name = ?")
        params.append(body.name.strip())

    if body.description is not None:
        updates.append("description = ?")
        params.append(body.description.strip() or None)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(label_id)
        cursor.execute(
            f"UPDATE labels SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()

    return {"success": True}


@router.post("/api/collections/{label_id}/games", tags=["Collections"])
def api_add_game_to_collection(label_id: int, body: AddGameRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Add a game to a collection."""
    game_id = body.game_id

    cursor = conn.cursor()

    # Check if collection exists
    cursor.execute("SELECT id FROM labels WHERE type = 'collection' AND id = ?", (label_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Collection not found")

    # Check if game exists
    cursor.execute("SELECT id FROM games WHERE id = ?", (game_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Game not found")

    # Try to add (ignore if already exists)
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO game_labels (label_id, game_id) VALUES (?, ?)",
            (label_id, game_id)
        )
        # Update collection's updated_at
        cursor.execute(
            "UPDATE labels SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (label_id,)
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True}


@router.delete("/api/collections/{label_id}/games/{game_id}", tags=["Collections"])
def api_remove_game_from_collection(label_id: int, game_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Remove a game from a collection."""
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM game_labels WHERE label_id = ? AND game_id = ?",
        (label_id, game_id)
    )

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Game not in collection")

    # Update collection's updated_at
    cursor.execute(
        "UPDATE labels SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (label_id,)
    )
    conn.commit()

    return {"success": True}


@router.get("/api/game/{game_id}/collections", tags=["Collections"])
def api_get_game_collections(game_id: int, conn: sqlite3.Connection = Depends(get_db)):
    """Get all collections a game belongs to."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.id, l.name
        FROM labels l
        JOIN game_labels gl ON l.id = gl.label_id
        WHERE gl.game_id = ? AND l.type = 'collection'
        ORDER BY l.name
    """, (game_id,))

    collections = [dict(c) for c in cursor.fetchall()]

    return collections
