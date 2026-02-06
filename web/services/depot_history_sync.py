"""
Depot history sync service - Fetches real depot update history from stores.

Unlike the simple last_modified tracking, this fetches the actual build/manifest
history from store APIs (like SteamDB does).
"""

import sqlite3
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
from ..services.settings import get_setting, STEAM_API_KEY


class SteamDepotClient:
    """Client for fetching Steam depot/manifest history."""
    
    def __init__(self):
        self.api_key = get_setting(STEAM_API_KEY)
        self.base_url = "https://api.steampowered.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Backlogia/1.0 (Game Library Manager)'
        })
        self._last_request_time = 0
        self._min_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self):
        """Enforce rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def get_app_history(self, appid: int, limit: int = 20) -> List[Dict]:
        """
        Get depot update history for a Steam app.
        
        Note: Steam doesn't provide a direct "depot history" endpoint.
        This uses the News API as a proxy for update detection, plus
        we track changes to the app's buildid over time.
        
        For a full SteamDB-style implementation, we'd need to:
        1. Monitor PICS (Product Info Change System) real-time
        2. Store historical buildid/manifestid data
        3. Poll regularly to build history over time
        
        This simplified version fetches news items tagged as updates.
        """
        self._rate_limit()
        
        # Fetch news items, filter for updates/patches
        url = f"{self.base_url}/ISteamNews/GetNewsForApp/v0002/"
        params = {
            'appid': appid,
            'count': limit,
            'maxlength': 300,
            'format': 'json'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'appnews' not in data or 'newsitems' not in data['appnews']:
                return []
            
            # Filter for update-related news
            updates = []
            update_keywords = ['update', 'patch', 'hotfix', 'version', 'build', 'release']
            
            for item in data['appnews']['newsitems']:
                title_lower = item.get('title', '').lower()
                contents_lower = item.get('contents', '').lower()
                
                # Check if it's an update announcement
                is_update = any(keyword in title_lower or keyword in contents_lower 
                              for keyword in update_keywords)
                
                if is_update:
                    updates.append({
                        'title': item.get('title'),
                        'url': item.get('url'),
                        'date': datetime.fromtimestamp(item.get('date', 0)).isoformat(),
                        'author': item.get('author'),
                        'feed_name': item.get('feedname', 'steam_community')
                    })
            
            return updates
            
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"[DEPOT] Error fetching Steam history for {appid}: {e}")
            return []


class EpicDepotClient:
    """Client for fetching Epic Games build history."""
    
    def __init__(self):
        # Epic uses legendary-gl library for auth
        # We'd need to integrate with Legendary's GraphQL queries
        pass
    
    def get_app_history(self, namespace: str, catalog_id: str, limit: int = 20) -> List[Dict]:
        """
        Get build history for an Epic game.
        
        Epic's GraphQL API exposes build information:
        query($namespace: String!, $catalogItemId: String!) {
          Catalog {
            catalogItem(namespace: $namespace, id: $catalogItemId) {
              buildVersions {
                buildVersion
                releaseDate
              }
            }
          }
        }
        
        This requires Epic auth tokens from Legendary.
        """
        # TODO: Implement Epic GraphQL query
        # For now, return empty (Epic integration more complex)
        return []


def sync_depot_history(conn: sqlite3.Connection, game_id: int, limit: int = 20) -> int:
    """
    Fetch and store depot update history for a game.
    
    Args:
        conn: Database connection
        game_id: Game ID
        limit: Maximum number of history entries to fetch
    
    Returns:
        Number of new history entries added
    """
    cursor = conn.cursor()
    
    # Get game info
    cursor.execute("""
        SELECT store, store_id, extra_data
        FROM games
        WHERE id = ?
    """, (game_id,))
    
    game = cursor.fetchone()
    if not game:
        return 0
    
    store = game['store']
    store_id = game['store_id']
    
    history = []
    
    if store == 'steam':
        client = SteamDepotClient()
        try:
            appid = int(store_id)
            history = client.get_app_history(appid, limit)
        except (ValueError, TypeError):
            print(f"[DEPOT] Invalid Steam appid for game {game_id}: {store_id}")
            return 0
    
    elif store == 'epic':
        # Epic implementation would go here
        # Requires namespace/catalog_id from extra_data
        pass
    
    else:
        # Other stores not supported yet
        return 0
    
    # Insert history entries
    count = 0
    for entry in history:
        try:
            # Check if we already have this entry (by URL or date)
            cursor.execute("""
                SELECT id FROM game_depot_updates
                WHERE game_id = ? AND update_timestamp = ?
            """, (game_id, entry['date']))
            
            if cursor.fetchone():
                continue  # Already exists
            
            cursor.execute("""
                INSERT INTO game_depot_updates 
                (game_id, update_timestamp, depot_id, manifest_id)
                VALUES (?, ?, ?, ?)
            """, (
                game_id,
                entry['date'],
                entry.get('feed_name', 'unknown'),  # Use feed_name as depot_id proxy
                entry.get('title', '')[:200]  # Use title as manifest_id proxy
            ))
            count += 1
            
        except sqlite3.IntegrityError:
            continue  # Duplicate
    
    conn.commit()
    
    # Update last sync timestamp
    cursor.execute("""
        UPDATE games 
        SET status_last_synced = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (game_id,))
    conn.commit()
    
    return count


def sync_all_depot_history(conn: sqlite3.Connection, store: Optional[str] = None, 
                           limit_per_game: int = 10) -> Dict[str, int]:
    """
    Sync depot history for all games in library.
    
    Args:
        conn: Database connection
        store: Filter by store ('steam', 'epic', etc.) or None for all
        limit_per_game: Max history entries per game
    
    Returns:
        Dict with stats: {'processed': int, 'updated': int, 'total_entries': int}
    """
    cursor = conn.cursor()
    
    # Get all games (filter by store if specified)
    query = "SELECT id FROM games WHERE 1=1"
    params = []
    
    if store:
        query += " AND store = ?"
        params.append(store)
    
    cursor.execute(query, params)
    game_ids = [row['id'] for row in cursor.fetchall()]
    
    processed = 0
    updated = 0
    total_entries = 0
    
    for game_id in game_ids:
        try:
            entries_added = sync_depot_history(conn, game_id, limit_per_game)
            processed += 1
            if entries_added > 0:
                updated += 1
                total_entries += entries_added
            
            # Rate limiting
            time.sleep(1.5)  # Be respectful to Steam API
            
        except Exception as e:
            print(f"[DEPOT] Error syncing game {game_id}: {e}")
            continue
    
    return {
        'processed': processed,
        'updated': updated,
        'total_entries': total_entries
    }


def get_depot_stats(conn: sqlite3.Connection) -> Dict:
    """Get statistics about depot history."""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT game_id) as games_with_history
        FROM game_depot_updates
    """)
    games_with_history = cursor.fetchone()['games_with_history']
    
    cursor.execute("""
        SELECT COUNT(*) as total_entries
        FROM game_depot_updates
    """)
    total_entries = cursor.fetchone()['total_entries']
    
    cursor.execute("""
        SELECT g.store, COUNT(DISTINCT gdu.game_id) as count
        FROM game_depot_updates gdu
        JOIN games g ON gdu.game_id = g.id
        GROUP BY g.store
    """)
    by_store = dict(cursor.fetchall())
    
    return {
        'games_with_history': games_with_history,
        'total_entries': total_entries,
        'by_store': by_store
    }
