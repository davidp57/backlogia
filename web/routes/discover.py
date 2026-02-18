# routes/discover.py
# Discover page routes

import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..dependencies import get_db
from ..utils.filters import EXCLUDE_HIDDEN_FILTER, build_query_filter_sql
from ..utils.helpers import parse_json_field

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Cache configuration
POPULARITY_CACHE_HOURS = 24  # DB cache duration
MEMORY_CACHE_TTL = 900  # 15 minutes for in-memory cache

# Module-level memory cache
_igdb_cache = {
    "data": None,
    "expires_at": 0,
    "igdb_ids_hash": None
}


def _hash_igdb_ids(igdb_ids):
    """Create a stable hash of the igdb_ids set for cache key."""
    return hashlib.md5(
        ",".join(str(i) for i in sorted(set(igdb_ids))).encode()
    ).hexdigest()


def get_cached_popularity(conn, igdb_ids, popularity_type=None):
    """
    Get cached popularity data from database (Tier 2 cache).
    Returns list of {game_id, value, popularity_type} or None if cache is stale/empty.
    """
    cursor = conn.cursor()
    
    # Check if we have recent cached data (within POPULARITY_CACHE_HOURS)
    cache_cutoff = (datetime.now() - timedelta(hours=POPULARITY_CACHE_HOURS)).isoformat()
    
    if popularity_type:
        cursor.execute("""
            SELECT igdb_id as game_id, popularity_value as value, popularity_type
            FROM popularity_cache
            WHERE igdb_id IN ({})
              AND popularity_type = ?
              AND cached_at > ?
            ORDER BY popularity_value DESC
        """.format(','.join('?' * len(igdb_ids))), igdb_ids + [popularity_type, cache_cutoff])
    else:
        cursor.execute("""
            SELECT igdb_id as game_id, popularity_value as value, popularity_type
            FROM popularity_cache
            WHERE igdb_id IN ({})
              AND cached_at > ?
            ORDER BY popularity_value DESC
        """.format(','.join('?' * len(igdb_ids))), igdb_ids + [cache_cutoff])
    
    results = cursor.fetchall()
    
    if not results:
        return None
    
    return [dict(row) for row in results]


def cache_popularity_data(conn, popularity_data):
    """
    Store popularity data in DB cache, replacing existing data for same igdb_id/type pairs.
    """
    if not popularity_data:
        return
    
    cursor = conn.cursor()
    
    # Use REPLACE to update or insert
    now = datetime.now().isoformat()
    cursor.executemany("""
        REPLACE INTO popularity_cache (igdb_id, popularity_type, popularity_value, cached_at)
        VALUES (?, ?, ?, ?)
    """, [
        (pop['game_id'], pop.get('popularity_type', 1), pop['value'], now)
        for pop in popularity_data
    ])
    
    conn.commit()


def _get_library_games(conn, stores=None, genres=None, queries=None):
    """Get all games with IGDB IDs from the library, with optional filters."""
    cursor = conn.cursor()
    
    # Build query with filters
    query = """SELECT id, name, store, igdb_id, igdb_cover_url, cover_image,
                      igdb_summary, description, igdb_screenshots, total_rating,
                      igdb_rating, aggregated_rating, genres, playtime_hours
               FROM games
               WHERE igdb_id IS NOT NULL AND igdb_id > 0""" + EXCLUDE_HIDDEN_FILTER
    params = []

    if stores:
        placeholders = ",".join("?" * len(stores))
        query += f" AND store IN ({placeholders})"
        params.extend(stores)

    if genres:
        genre_conditions = []
        for genre in genres:
            genre_conditions.append("LOWER(genres) LIKE ?")
            params.append(f'%"{genre.lower()}"%')
        query += " AND (" + " OR ".join(genre_conditions) + ")"
    
    if queries:
        filter_sql = build_query_filter_sql(queries)
        if filter_sql:
            query += f" AND {filter_sql}"

    query += " ORDER BY total_rating DESC NULLS LAST"
    cursor.execute(query, params)
    return cursor.fetchall()


def _build_igdb_mapping(library_games):
    """Build igdb_id -> game data mapping and deduplicated unique games list."""
    igdb_to_local = {}
    igdb_ids = []
    unique_games = []
    seen_igdb_ids = set()

    for game in library_games:
        igdb_id = game["igdb_id"]
        igdb_ids.append(igdb_id)
        igdb_to_local[igdb_id] = dict(game)
        if igdb_id not in seen_igdb_ids:
            seen_igdb_ids.add(igdb_id)
            unique_games.append(dict(game))

    return igdb_to_local, igdb_ids, unique_games


def _derive_db_categories(conn, stores=None, genres=None, queries=None):
    """Derive category lists using optimized UNION ALL query."""
    cursor = conn.cursor()
    
    # Build base filters
    base_filters = "WHERE igdb_id IS NOT NULL AND igdb_id > 0" + EXCLUDE_HIDDEN_FILTER
    params = []
    
    # Apply store filters
    if stores:
        placeholders = ",".join("?" * len(stores))
        base_filters += f" AND store IN ({placeholders})"
        params.extend(stores * 5)  # 5 categories
    
    # Apply genre filters
    genre_filter = ""
    if genres:
        genre_conditions = []
        for genre in genres:
            genre_conditions.append("LOWER(genres) LIKE ?")
        genre_filter = " AND (" + " OR ".join(genre_conditions) + ")"
    
    # Apply query filters
    query_filter = ""
    if queries:
        filter_sql = build_query_filter_sql(queries)
        if filter_sql:
            query_filter = f" AND {filter_sql}"
    
    combined_filters = base_filters + genre_filter + query_filter
    
    # Add genre params for each category
    if genres:
        for _ in range(5):  # 5 categories
            params.extend([f'%"{g.lower()}"%' for g in genres])
    
    combined_query = f"""
        SELECT * FROM (
            SELECT 'highly_rated' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {combined_filters} AND total_rating >= 90
            ORDER BY total_rating DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'hidden_gems' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {combined_filters} AND total_rating >= 75 AND total_rating < 90 AND aggregated_rating IS NULL
            ORDER BY igdb_rating DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'most_played' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {combined_filters} AND playtime_hours > 0
            ORDER BY playtime_hours DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'critic_favorites' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {combined_filters} AND aggregated_rating >= 80
            ORDER BY aggregated_rating DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'random_picks' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {combined_filters}
            ORDER BY RANDOM()
            LIMIT 10
        )
    """
    
    cursor.execute(combined_query, params)
    all_categories = cursor.fetchall()
    
    # Split results by category
    highly_rated = []
    hidden_gems = []
    most_played = []
    critic_favorites = []
    random_picks = []
    
    for row in all_categories:
        game_dict = dict(row)
        category = game_dict.pop('category')
        
        if category == 'highly_rated':
            highly_rated.append(game_dict)
        elif category == 'hidden_gems':
            hidden_gems.append(game_dict)
        elif category == 'most_played':
            most_played.append(game_dict)
        elif category == 'critic_favorites':
            critic_favorites.append(game_dict)
        elif category == 'random_picks':
            random_picks.append(game_dict)
    
    return highly_rated, hidden_gems, most_played, critic_favorites, random_picks


def _empty_igdb_result():
    """Return empty IGDB sections structure."""
    return {
        "popularity_source": "rating",
        "featured_games": [],
        "igdb_visits": [],
        "want_to_play": [],
        "playing": [],
        "played": [],
        "steam_peak_24h": [],
        "steam_positive_reviews": [],
    }


def _fetch_igdb_sections(conn, igdb_ids, igdb_to_local):
    """
    Fetch all IGDB popularity data with 2-tier caching:
    Tier 1: Memory cache (15min) - fastest
    Tier 2: DB cache (24h) - avoids IGDB API calls
    Tier 3: IGDB API - slowest, updates both caches
    """
    from ..services.igdb_sync import (
        IGDBClient,
        POPULARITY_TYPE_IGDB_VISITS, POPULARITY_TYPE_IGDB_WANT_TO_PLAY,
        POPULARITY_TYPE_IGDB_PLAYING, POPULARITY_TYPE_IGDB_PLAYED,
        POPULARITY_TYPE_STEAM_PEAK_24H, POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS
    )
    
    if not igdb_ids:
        return _empty_igdb_result()

    ids_hash = _hash_igdb_ids(igdb_ids)
    now = time.time()

    # Tier 1: Check memory cache (fastest - 0ms)
    if (_igdb_cache["data"] is not None
            and _igdb_cache["igdb_ids_hash"] == ids_hash
            and now < _igdb_cache["expires_at"]):
        print("Using Tier 1 cache (memory)")
        return _igdb_cache["data"]

    # Tier 2: Check DB cache (fast - no IGDB API call)
    cached_data = get_cached_popularity(conn, igdb_ids)
    if cached_data:
        print(f"Using Tier 2 cache (DB) - {len(cached_data)} entries")
        
        def _resolve_from_cache(pop_type=None):
            """Map cached popularity to local game data."""
            type_data = [p for p in cached_data if p.get('popularity_type') == pop_type] if pop_type else cached_data
            result = []
            seen = set()
            for pop in type_data:
                gid = pop.get("game_id")
                if gid in igdb_to_local and gid not in seen:
                    gdata = igdb_to_local[gid].copy()
                    gdata["popularity_value"] = pop.get("value", 0)
                    result.append(gdata)
                    seen.add(gid)
            return result
        
        result = {
            "popularity_source": "igdb_popularity",
            "featured_games": _resolve_from_cache()[:20],
            "igdb_visits": _resolve_from_cache(POPULARITY_TYPE_IGDB_VISITS)[:10],
            "want_to_play": _resolve_from_cache(POPULARITY_TYPE_IGDB_WANT_TO_PLAY)[:10],
            "playing": _resolve_from_cache(POPULARITY_TYPE_IGDB_PLAYING)[:10],
            "played": _resolve_from_cache(POPULARITY_TYPE_IGDB_PLAYED)[:10],
            "steam_peak_24h": _resolve_from_cache(POPULARITY_TYPE_STEAM_PEAK_24H)[:10],
            "steam_positive_reviews": _resolve_from_cache(POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS)[:10],
        }
        
        # Promote to memory cache
        _igdb_cache["data"] = result
        _igdb_cache["expires_at"] = now + MEMORY_CACHE_TTL
        _igdb_cache["igdb_ids_hash"] = ids_hash
        
        return result

    # Tier 3: Fetch from IGDB API with parallelization
    try:
        print("Cache miss - fetching from IGDB API (Tier 3)")
        client = IGDBClient()

        pop_types = {
            "igdb_visits": POPULARITY_TYPE_IGDB_VISITS,
            "want_to_play": POPULARITY_TYPE_IGDB_WANT_TO_PLAY,
            "playing": POPULARITY_TYPE_IGDB_PLAYING,
            "played": POPULARITY_TYPE_IGDB_PLAYED,
            "steam_peak_24h": POPULARITY_TYPE_STEAM_PEAK_24H,
            "steam_positive_reviews": POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS,
        }

        def _resolve_popularity(pop_data):
            """Map IGDB popularity response to local game data."""
            result = []
            seen = set()
            for pop in pop_data:
                gid = pop.get("game_id")
                if gid in igdb_to_local and gid not in seen:
                    gdata = igdb_to_local[gid].copy()
                    gdata["popularity_value"] = pop.get("value", 0)
                    result.append(gdata)
                    seen.add(gid)
            return result

        results = {}
        all_popularity_data = []

        with ThreadPoolExecutor(max_workers=7) as executor:
            # Submit all 7 IGDB calls in parallel
            future_popular = executor.submit(
                client.get_popular_games, igdb_ids, None, 100
            )
            futures_by_key = {
                executor.submit(
                    client.get_popular_games, igdb_ids, pop_type, 10
                ): key
                for key, pop_type in pop_types.items()
            }

            # Collect general popularity result
            popularity_data = future_popular.result()
            popular_games = _resolve_popularity(popularity_data)
            popularity_source = "igdb_popularity" if popular_games else "rating"
            
            # Store for DB caching
            for pop in popularity_data:
                pop['popularity_type'] = 1  # Default type
            all_popularity_data.extend(popularity_data)

            # Collect typed results
            for future, key in futures_by_key.items():
                type_data = future.result()
                results[key] = _resolve_popularity(type_data)
                
                # Add type and store for DB caching
                pop_type_id = pop_types[key]
                for pop in type_data:
                    pop['popularity_type'] = pop_type_id
                all_popularity_data.extend(type_data)

        featured_games = popular_games[:20] if popular_games else []

        result = {
            "popularity_source": popularity_source,
            "featured_games": featured_games,
            "igdb_visits": results.get("igdb_visits", []),
            "want_to_play": results.get("want_to_play", []),
            "playing": results.get("playing", []),
            "played": results.get("played", []),
            "steam_peak_24h": results.get("steam_peak_24h", []),
            "steam_positive_reviews": results.get("steam_positive_reviews", []),
        }

        # Store in DB cache (Tier 2)
        if all_popularity_data:
            cache_popularity_data(conn, all_popularity_data)
            print(f"Stored {len(all_popularity_data)} entries in DB cache")
        
        # Store in memory cache (Tier 1)
        _igdb_cache["data"] = result
        _igdb_cache["expires_at"] = now + MEMORY_CACHE_TTL
        _igdb_cache["igdb_ids_hash"] = ids_hash

        return result

    except Exception as e:
        print(f"Could not fetch IGDB popularity data: {e}")
        return _empty_igdb_result()


def _game_to_json(game):
    """Convert a game dict to a JSON-safe dict with parsed JSON fields."""
    return {
        "id": game["id"],
        "name": game["name"],
        "store": game.get("store", ""),
        "igdb_cover_url": game.get("igdb_cover_url") or "",
        "cover_image": game.get("cover_image") or "",
        "igdb_summary": game.get("igdb_summary") or "",
        "description": game.get("description") or "",
        "igdb_screenshots": parse_json_field(game.get("igdb_screenshots")),
        "genres": parse_json_field(game.get("genres")),
        "total_rating": game.get("total_rating"),
        "igdb_rating": game.get("igdb_rating"),
        "aggregated_rating": game.get("aggregated_rating"),
        "playtime_hours": game.get("playtime_hours"),
    }


@router.get("/discover", response_class=HTMLResponse)
def discover(
    request: Request,
    stores: list[str] = Query(default=[]),
    genres: list[str] = Query(default=[]),
    queries: list[str] = Query(default=[]),
    exclude_streaming: bool = False,
    no_igdb: bool = False,
    conn: sqlite3.Connection = Depends(get_db)
):
    """Discover page - renders immediately with DB data, IGDB sections load via AJAX."""
    from ..utils.filters import QUERY_DISPLAY_NAMES, QUERY_CATEGORIES, QUERY_DESCRIPTIONS
    
    cursor = conn.cursor()
    
    # Get store and genre counts for filters
    cursor.execute("""
        SELECT store, COUNT(*) as count
        FROM games
        WHERE igdb_id IS NOT NULL AND igdb_id > 0 AND hidden = 0
        GROUP BY store
        ORDER BY count DESC
    """)
    store_counts = dict(cursor.fetchall())
    
    cursor.execute("""
        SELECT DISTINCT genres
        FROM games
        WHERE genres IS NOT NULL AND genres != '[]' AND igdb_id IS NOT NULL AND igdb_id > 0 AND hidden = 0
    """)
    genre_counts = {}
    for row in cursor.fetchall():
        try:
            genres_list = json.loads(row[0])
            for genre in genres_list:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    genre_counts = dict(sorted(genre_counts.items(), key=lambda x: x[1], reverse=True))
    
    # Get DB-based categories with filters applied
    highly_rated, hidden_gems, most_played, critic_favorites, random_picks = (
        _derive_db_categories(conn, stores, genres, queries)
    )
    
    # Get library games for IGDB check
    library_games = _get_library_games(conn, stores, genres, queries)
    igdb_to_local, igdb_ids, unique_games = _build_igdb_mapping(library_games)
    has_igdb_ids = bool(igdb_ids)
    
    # Calculate query filter counts
    from ..utils.helpers import get_query_filter_counts
    query_filter_counts = {}
    if library_games:
        query_filter_counts = get_query_filter_counts(cursor)

    # Get collections for the filter dropdown
    cursor.execute("""
        SELECT c.id, c.name, COUNT(cg.game_id) as game_count
        FROM collections c
        LEFT JOIN collection_games cg ON c.id = cg.collection_id
        GROUP BY c.id
        ORDER BY c.name
    """)
    collections = [{"id": row[0], "name": row[1], "game_count": row[2]} for row in cursor.fetchall()]

    return templates.TemplateResponse(
        request,
        "discover.html",
        {
            "highly_rated": highly_rated,
            "hidden_gems": hidden_gems,
            "most_played": most_played,
            "critic_favorites": critic_favorites,
            "random_picks": random_picks,
            "has_igdb_ids": has_igdb_ids,
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
            # Advanced filters (global)
            "current_exclude_streaming": exclude_streaming,
            "current_no_igdb": no_igdb,
            "collections": collections,
            "show_search": False,
            "show_sort": False,
            "show_actions": True,
        }
    )


@router.get("/api/discover/igdb-sections")
def discover_igdb_sections(
    stores: list[str] = Query(default=[]),
    genres: list[str] = Query(default=[]),
    queries: list[str] = Query(default=[]),
    conn: sqlite3.Connection = Depends(get_db)
):
    """API endpoint returning IGDB popularity sections as JSON with filter support."""
    library_games = _get_library_games(conn, stores, genres, queries)
    igdb_to_local, igdb_ids, unique_games = _build_igdb_mapping(library_games)

    igdb_data = _fetch_igdb_sections(conn, igdb_ids, igdb_to_local)

    # If no IGDB popularity data, use rating-based fallback
    if not igdb_data["featured_games"] and unique_games:
        igdb_data["popularity_source"] = "rating"
        igdb_data["featured_games"] = [
            g for g in unique_games if g["total_rating"]
        ][:20]

    return JSONResponse(content={
        "popularity_source": igdb_data["popularity_source"],
        "featured_games": [_game_to_json(g) for g in igdb_data["featured_games"]],
        "igdb_visits": [_game_to_json(g) for g in igdb_data["igdb_visits"]],
        "want_to_play": [_game_to_json(g) for g in igdb_data["want_to_play"]],
        "playing": [_game_to_json(g) for g in igdb_data["playing"]],
        "played": [_game_to_json(g) for g in igdb_data["played"]],
        "steam_peak_24h": [_game_to_json(g) for g in igdb_data["steam_peak_24h"]],
        "steam_positive_reviews": [_game_to_json(g) for g in igdb_data["steam_positive_reviews"]],
    })
