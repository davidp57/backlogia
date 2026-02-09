# routes/discover.py
# Discover page routes

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..dependencies import get_db
from ..utils.filters import EXCLUDE_HIDDEN_FILTER, build_query_filter_sql
from ..utils.helpers import parse_json_field

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Cache duration for popularity data (24 hours)
POPULARITY_CACHE_HOURS = 24


def get_cached_popularity(conn, igdb_ids, popularity_type=None):
    """
    Get cached popularity data from database.
    Returns list of {game_id, value, popularity_type} or None if cache is stale/empty.
    """
    cursor = conn.cursor()
    
    # Check if we have recent cached data (within POPULARITY_CACHE_HOURS)
    # Convert to ISO string to avoid Python 3.12+ datetime adapter deprecation warning
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
    Store popularity data in cache, replacing existing data for same igdb_id/type pairs.
    """
    if not popularity_data:
        return
    
    cursor = conn.cursor()
    
    # Use REPLACE to update or insert
    # Convert datetime to ISO string to avoid Python 3.12+ datetime adapter deprecation warning
    now = datetime.now().isoformat()
    cursor.executemany("""
        REPLACE INTO popularity_cache (igdb_id, popularity_type, popularity_value, cached_at)
        VALUES (?, ?, ?, ?)
    """, [
        (pop['game_id'], pop.get('popularity_type', 1), pop['value'], now)
        for pop in popularity_data
    ])
    
    conn.commit()


@router.get("/discover", response_class=HTMLResponse)
def discover(
    request: Request,
    stores: list[str] = Query(default=[]),
    genres: list[str] = Query(default=[]),
    queries: list[str] = Query(default=[]),
    conn: sqlite3.Connection = Depends(get_db)
):
    """Discover page - showcase popular games from your library."""
    # Import here to avoid circular imports
    from ..services.igdb_sync import (
        IGDBClient,
        POPULARITY_TYPE_IGDB_VISITS, POPULARITY_TYPE_IGDB_WANT_TO_PLAY,
        POPULARITY_TYPE_IGDB_PLAYING, POPULARITY_TYPE_IGDB_PLAYED,
        POPULARITY_TYPE_STEAM_PEAK_24H, POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS
    )
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
    library_games = cursor.fetchall()

    # Create a mapping of igdb_id to local game data
    igdb_to_local = {}
    igdb_ids = []
    for game in library_games:
        igdb_id = game["igdb_id"]
        igdb_ids.append(igdb_id)
        igdb_to_local[igdb_id] = dict(game)

    # Try to get popularity data from IGDB
    popular_games = []
    popularity_source = "rating"  # Default fallback

    # Popularity-based sections (will be populated if IGDB API or cache succeeds)
    igdb_visits = []
    want_to_play = []
    playing = []
    played = []
    steam_peak_24h = []
    steam_positive_reviews = []

    if igdb_ids:
        # Try to get from cache first
        cached_data = get_cached_popularity(conn, igdb_ids)
        
        if cached_data:
            # Use cached data
            print(f"Using cached popularity data ({len(cached_data)} entries)")
            popularity_source = "igdb_popularity"
            
            # Build popular_games from cache
            seen_ids = set()
            for pop in cached_data:
                game_id = pop.get("game_id")
                if game_id in igdb_to_local and game_id not in seen_ids:
                    game_data = igdb_to_local[game_id].copy()
                    game_data["popularity_value"] = pop.get("value", 0)
                    popular_games.append(game_data)
                    seen_ids.add(game_id)
            
            # Helper function to fetch games by popularity type from cache
            def fetch_from_cache_by_type(pop_type, limit=10):
                type_data = [p for p in cached_data if p.get('popularity_type') == pop_type]
                result = []
                seen = set()
                for pop in type_data[:limit]:
                    gid = pop.get("game_id")
                    if gid in igdb_to_local and gid not in seen:
                        gdata = igdb_to_local[gid].copy()
                        gdata["popularity_value"] = pop.get("value", 0)
                        result.append(gdata)
                        seen.add(gid)
                return result
            
            # Fetch each popularity type from cache
            igdb_visits = fetch_from_cache_by_type(POPULARITY_TYPE_IGDB_VISITS)
            want_to_play = fetch_from_cache_by_type(POPULARITY_TYPE_IGDB_WANT_TO_PLAY)
            playing = fetch_from_cache_by_type(POPULARITY_TYPE_IGDB_PLAYING)
            played = fetch_from_cache_by_type(POPULARITY_TYPE_IGDB_PLAYED)
            steam_peak_24h = fetch_from_cache_by_type(POPULARITY_TYPE_STEAM_PEAK_24H)
            steam_positive_reviews = fetch_from_cache_by_type(POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS)
        else:
            # Cache miss - fetch from IGDB API and cache results
            try:
                print("Cache miss - fetching from IGDB API...")
                client = IGDBClient()

                # Fetch all popularity types and cache them
                all_popularity_data = []
                
                for pop_type in [POPULARITY_TYPE_IGDB_VISITS, POPULARITY_TYPE_IGDB_WANT_TO_PLAY,
                               POPULARITY_TYPE_IGDB_PLAYING, POPULARITY_TYPE_IGDB_PLAYED,
                               POPULARITY_TYPE_STEAM_PEAK_24H, POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS]:
                    pop_data = client.get_popular_games(igdb_ids, popularity_type=pop_type, limit=100)
                    if pop_data:
                        # Add popularity_type to each entry
                        for entry in pop_data:
                            entry['popularity_type'] = pop_type
                        all_popularity_data.extend(pop_data)
                
                if all_popularity_data:
                    # Cache the results
                    cache_popularity_data(conn, all_popularity_data)
                    print(f"Cached {len(all_popularity_data)} popularity entries")
                    
                    popularity_source = "igdb_popularity"
                    
                    # Build popular_games from API data
                    seen_ids = set()
                    for pop in all_popularity_data:
                        game_id = pop.get("game_id")
                        if game_id in igdb_to_local and game_id not in seen_ids:
                            game_data = igdb_to_local[game_id].copy()
                            game_data["popularity_value"] = pop.get("value", 0)
                            popular_games.append(game_data)
                            seen_ids.add(game_id)
                    
                    # Helper function to fetch games by popularity type
                    def fetch_by_popularity_type(pop_type, limit=10):
                        type_data = [p for p in all_popularity_data if p.get('popularity_type') == pop_type]
                        result = []
                        seen = set()
                        for pop in type_data[:limit]:
                            gid = pop.get("game_id")
                            if gid in igdb_to_local and gid not in seen:
                                gdata = igdb_to_local[gid].copy()
                                gdata["popularity_value"] = pop.get("value", 0)
                                result.append(gdata)
                                seen.add(gid)
                        return result
                    
                    # Fetch each popularity type
                    igdb_visits = fetch_by_popularity_type(POPULARITY_TYPE_IGDB_VISITS)
                    want_to_play = fetch_by_popularity_type(POPULARITY_TYPE_IGDB_WANT_TO_PLAY)
                    playing = fetch_by_popularity_type(POPULARITY_TYPE_IGDB_PLAYING)
                    played = fetch_by_popularity_type(POPULARITY_TYPE_IGDB_PLAYED)
                    steam_peak_24h = fetch_by_popularity_type(POPULARITY_TYPE_STEAM_PEAK_24H)
                    steam_positive_reviews = fetch_by_popularity_type(POPULARITY_TYPE_STEAM_POSITIVE_REVIEWS)

            except Exception as e:
                print(f"Could not fetch IGDB popularity data: {e}")

    # Fallback: use total_rating if no popularity data
    if not popular_games:
        popularity_source = "rating"
        popular_games = [dict(g) for g in library_games if g["total_rating"]]

    # Limit to top games for display
    featured_games = popular_games[:20] if popular_games else []

    # Get all category breakdowns in a single optimized query using UNION ALL
    # Each subquery needs to be wrapped in parentheses to allow ORDER BY + LIMIT
    base_filters = "WHERE igdb_id IS NOT NULL AND igdb_id > 0" + EXCLUDE_HIDDEN_FILTER
    
    combined_query = f"""
        SELECT * FROM (
            SELECT 'highly_rated' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {base_filters} AND total_rating >= 90
            ORDER BY total_rating DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'hidden_gems' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {base_filters} AND total_rating >= 75 AND total_rating < 90 AND aggregated_rating IS NULL
            ORDER BY igdb_rating DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'most_played' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {base_filters} AND playtime_hours > 0
            ORDER BY playtime_hours DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'critic_favorites' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {base_filters} AND aggregated_rating >= 80
            ORDER BY aggregated_rating DESC
            LIMIT 10
        )
        
        UNION ALL
        
        SELECT * FROM (
            SELECT 'random_picks' as category, id, name, store, igdb_id, igdb_cover_url, cover_image,
                   igdb_summary, description, igdb_screenshots, total_rating,
                   igdb_rating, aggregated_rating, genres, playtime_hours
            FROM games
            {base_filters}
            ORDER BY RANDOM()
            LIMIT 10
        )
    """
    
    cursor.execute(combined_query)
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

    return templates.TemplateResponse(
        request,
        "discover.html",
        {
            "featured_games": featured_games,
            "highly_rated": highly_rated,
            "hidden_gems": hidden_gems,
            "most_played": most_played,
            "critic_favorites": critic_favorites,
            "random_picks": random_picks,
            "popularity_source": popularity_source,
            "igdb_visits": igdb_visits,
            "want_to_play": want_to_play,
            "playing": playing,
            "played": played,
            "steam_peak_24h": steam_peak_24h,
            "steam_positive_reviews": steam_positive_reviews,
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
            "query_filter_counts": {},  # Empty for discover page (performance)
            "show_search": False,  # No search on discover page
            "show_sort": False,  # No sort on discover page
            "show_actions": True,
        }
    )
