# status_sync.py
# Detects and syncs game development status (Early Access, Alpha, Beta, Released)
# and tracks update timestamps across multiple stores

import sqlite3
import requests
import time
from datetime import datetime, timedelta


class SteamStatusDetector:
    """Detect development status for Steam games."""
    
    APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
    
    @staticmethod
    def get_status(appid):
        """
        Get development status for a Steam game.
        
        Returns:
            Tuple of (status, version) where status is one of:
            'early_access', 'released', or None
        """
        headers = {
            'User-Agent': 'Backlogia/1.0 (Game Library Manager; +https://github.com/sam1am/backlogia)'
        }
        
        try:
            response = requests.get(
                SteamStatusDetector.APP_DETAILS_URL,
                params={'appids': appid},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if str(appid) not in data or not data[str(appid)].get('success'):
                return (None, None)
            
            app_data = data[str(appid)]['data']
            
            # Check for Early Access (category 29)
            categories = app_data.get('categories', [])
            for category in categories:
                if category.get('id') == 29:  # Early Access category
                    return ('early_access', None)
            
            # If not Early Access, assume released
            return ('released', None)
            
        except requests.exceptions.RequestException as e:
            print(f"[STATUS] Error fetching Steam status for {appid}: {e}")
            return (None, None)
        except Exception as e:
            print(f"[STATUS] Unexpected error for Steam {appid}: {e}")
            return (None, None)


class EpicStatusDetector:
    """Detect development status for Epic games using Legendary metadata."""
    
    @staticmethod
    def get_status_from_metadata(metadata):
        """
        Extract status from Epic metadata (JSON from Legendary).
        
        Args:
            metadata: Dict or JSON string of game metadata
        
        Returns:
            Tuple of (status, version)
        """
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                return (None, None)
        
        if not isinstance(metadata, dict):
            return (None, None)
        
        # Check custom attributes for early access indicators
        custom_attrs = metadata.get('customAttributes', {})
        
        # Look for early access flags (various keys used by Epic)
        early_access_keys = ['EarlyAccess', 'earlyAccess', 'isEarlyAccess']
        for key in early_access_keys:
            if key in custom_attrs:
                value = custom_attrs[key].get('value', '').lower()
                if value in ['true', '1', 'yes']:
                    return ('early_access', None)
        
        # Check release info for pre-release indicators
        release_info = metadata.get('releaseInfo', [])
        if release_info and len(release_info) > 0:
            app_status = release_info[0].get('appStatus')
            if app_status and 'early' in app_status.lower():
                return ('early_access', None)
        
        # Default to released if no early access indicators
        return ('released', None)


class GOGStatusDetector:
    """Detect development status for GOG games (limited capability)."""
    
    @staticmethod
    def get_status_from_igdb(igdb_status):
        """
        Extract status from IGDB data (fallback for GOG).
        
        Args:
            igdb_status: Status field from IGDB
        
        Returns:
            Tuple of (status, version)
        """
        # GOG doesn't have a reliable API for status
        # This is a placeholder for IGDB-based detection
        # Implementation depends on IGDB status field structure
        return (None, None)


def sync_game_status(conn, game_id):
    """
    Sync development status for a single game.
    
    Args:
        conn: Database connection
        game_id: Game ID to sync
    
    Returns:
        True if status was updated, False otherwise
    """
    cursor = conn.cursor()
    
    # Get game info
    cursor.execute("""
        SELECT store, store_id, name, extra_data, igdb_id 
        FROM games WHERE id = ?
    """, (game_id,))
    result = cursor.fetchone()
    
    if not result:
        return False
    
    store, store_id, name, extra_data, igdb_id = result
    status = None
    version = None
    
    # Detect status based on store
    if store == 'steam' and store_id:
        status, version = SteamStatusDetector.get_status(store_id)
    elif store == 'epic' and extra_data:
        status, version = EpicStatusDetector.get_status_from_metadata(extra_data)
    elif store == 'gog' and igdb_id:
       # Try IGDB fallback for GOG
        # For now, leave as None - requires IGDB integration
        pass
    
    if status:
        cursor.execute("""
            UPDATE games SET 
                development_status = ?,
                game_version = ?,
                status_last_synced = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, version, game_id))
        conn.commit()
        print(f"[STATUS] {name}: {status}")
        return True
    else:
        # Update timestamp even if no status detected
        cursor.execute("""
            UPDATE games SET status_last_synced = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (game_id,))
        conn.commit()
        return False


def _should_skip_sync(cursor, game_id, days=7):
    """Check if game status was synced recently (within days)."""
    cursor.execute("""
        SELECT status_last_synced FROM games WHERE id = ?
    """, (game_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        last_synced = datetime.fromisoformat(result[0])
        time_since = datetime.now() - last_synced
        return time_since < timedelta(days=days)
    return False


def sync_all_statuses(conn, store=None, force=False, progress_callback=None):
    """
    Sync development status for all games (or filtered by store).
    
    Args:
        conn: Database connection
        store: Optional store filter ('steam', 'epic', 'gog', None for all)
        force: If True, sync all games; if False, skip recently synced (7 days)
        progress_callback: Optional callback function(current, total, message)
    
    Returns:
        Tuple of (synced_count, failed_count)
    """
    cursor = conn.cursor()
    
    # Build query based on store filter
    if store:
        cursor.execute("""
            SELECT id, name FROM games 
            WHERE store = ? AND store_id IS NOT NULL
            ORDER BY name
        """, (store,))
    else:
        cursor.execute("""
            SELECT id, name FROM games 
            WHERE store_id IS NOT NULL
            ORDER BY name
        """)
    
    games = cursor.fetchall()
    
    if not games:
        print("[STATUS] No games found to sync")
        return (0, 0)
    
    # Filter by last sync time if not force
    if not force:
        games_to_process = []
        for game_id, name in games:
            if not _should_skip_sync(cursor, game_id, days=7):
                games_to_process.append((game_id, name))
        games = games_to_process
    
    total = len(games)
    if total == 0:
        print("[STATUS] No games need status sync (all recently synced)")
        return (0, 0)
    
    print(f"[STATUS] Syncing status for {total} games...")
    
    synced = 0
    failed = 0
    
    for i, (game_id, name) in enumerate(games):
        completed = i + 1
        
        # Report progress
        if progress_callback:
            progress_callback(completed, total, f"Processing: {name[:50]}...")
        
        try:
            if sync_game_status(conn, game_id):
                synced += 1
            # Small delay to avoid hammering APIs
            time.sleep(0.5)
        except Exception as e:
            failed += 1
            print(f"[STATUS] [{completed}/{total}] Error for {name}: {e}")
    
    print(f"[STATUS] Sync complete: {synced} updated, {failed} failed")
    return (synced, failed)


def track_update_timestamp(conn, game_id, store, store_data):
    """
    Track update timestamp during store import.
    Compares last_modified with previous value and creates depot update record if changed.
    
    Args:
        conn: Database connection  
        game_id: Game ID
        store: Store name ('steam', 'epic', 'gog')
        store_data: Dict with store-specific data including last_modified timestamp
    
    Returns:
        True if update was detected, False otherwise
    """
    cursor = conn.cursor()
    
    # Get current last_modified from database
    cursor.execute("""
        SELECT last_modified FROM games WHERE id = ?
    """, (game_id,))
    result = cursor.fetchone()
    
    if not result:
        return False
    
    old_timestamp = result[0]
    new_timestamp = store_data.get('last_modified')
    
    if not new_timestamp:
        return False
    
    # If this is first sync (no old timestamp), just update - don't create record
    if not old_timestamp:
        cursor.execute("""
            UPDATE games SET last_modified = ? WHERE id = ?
        """, (new_timestamp, game_id))
        conn.commit()
        return False
    
    # Compare timestamps - create depot update record if changed
    if new_timestamp != old_timestamp:
        try:
            # Parse timestamps for comparison
            old_dt = datetime.fromisoformat(old_timestamp)
            new_dt = datetime.fromisoformat(new_timestamp)
            
            if new_dt > old_dt:
                # Game was updated!
                cursor.execute("""
                    INSERT INTO game_depot_updates (game_id, update_timestamp)
                    VALUES (?, ?)
                """, (game_id, new_timestamp))
                
                cursor.execute("""
                    UPDATE games SET last_modified = ? WHERE id = ?
                """, (new_timestamp, game_id))
                
                conn.commit()
                return True
        except (ValueError, TypeError) as e:
            print(f"[STATUS] Error parsing timestamps for game {game_id}: {e}")
    
    return False


def get_status_stats(conn):
    """Get statistics about status tracking."""
    cursor = conn.cursor()
    
    # Count by status
    cursor.execute("""
        SELECT development_status, COUNT(*) 
        FROM games 
        WHERE development_status IS NOT NULL
        GROUP BY development_status
    """)
    status_counts = dict(cursor.fetchall())
    
    # Games with status
    cursor.execute("""
        SELECT COUNT(*) FROM games WHERE development_status IS NOT NULL
    """)
    games_with_status = cursor.fetchone()[0]
    
    # Most recent sync
    cursor.execute("""
        SELECT MAX(status_last_synced) FROM games
    """)
    last_synced = cursor.fetchone()[0]
    
    return {
        'status_counts': status_counts,
        'games_with_status': games_with_status,
        'last_synced': last_synced
    }


def sync_all_statuses_job(job_id: str, store: str | None = None, force: bool = False):
    """
    Job function to sync development status for all games sequentially.
    Uses job system for progress tracking.
    
    Args:
        job_id: Job ID for progress tracking
        store: Optional store filter ('steam', 'epic', 'gog', or None for all)
        force: If True, sync all games; if False, skip recently synced (7 days)
    """
    from ..config import DATABASE_PATH
    from .jobs import update_job_progress, complete_job, fail_job, is_job_cancelled
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Build query with optional store filter
        query = """
            SELECT id, store, store_id, name 
            FROM games 
            WHERE store IN ('steam', 'epic', 'gog') AND store_id IS NOT NULL
        """
        params = []
        
        if store:
            query += " AND store = ?"
            params.append(store)
        
        query += " ORDER BY name"
        
        cursor.execute(query, params)
        games = cursor.fetchall()
        
        if not games:
            complete_job(job_id, "0", "No games found for status sync")
            conn.close()
            return
        
        # Filter by cache if not force
        if not force:
            games_to_process = []
            cursor_check = conn.cursor()
            for game_id, game_store, store_id, name in games:
                if not _should_skip_sync(cursor_check, game_id, days=7):
                    games_to_process.append((game_id, game_store, store_id, name))
            games = games_to_process
        
        total = len(games)
        if total == 0:
            complete_job(job_id, "0", "All games recently synced (cache valid)")
            conn.close()
            return
        
        store_filter = store or "all"
        print(f"[STATUS JOB {job_id}] Syncing status for {total} games (store: {store_filter})...")
        update_job_progress(job_id, 0, total, f"Starting sync for {total} games")
        
        synced = 0
        failed = 0
        
        # Process games sequentially
        for idx, (game_id, game_store, store_id, name) in enumerate(games, 1):
            # Check if job has been cancelled
            if is_job_cancelled(job_id):
                conn.close()
                print(f"[STATUS JOB {job_id}] Cancelled by user at {idx}/{total}")
                return
            
            try:
                update_job_progress(job_id, idx - 1, total, f"Processing: {name[:50]}...")
                
                # Sync status for this game
                result = sync_game_status(conn, game_id)
                
                if result:
                    synced += 1
                    print(f"[STATUS JOB {job_id}] [{idx}/{total}] {name}: synced")
                else:
                    print(f"[STATUS JOB {job_id}] [{idx}/{total}] No status: {name}")
                    
            except Exception as e:
                failed += 1
                print(f"[STATUS JOB {job_id}] [{idx}/{total}] Exception for {name}: {e}")
        
        conn.close()
        
        # Complete job
        result_msg = f"{synced} games synced, {failed} failed"
        complete_job(job_id, str(synced), result_msg)
        print(f"[STATUS JOB {job_id}] Complete: {result_msg}")
        
    except Exception as e:
        print(f"[STATUS JOB {job_id}] Fatal error: {e}")
        fail_job(job_id, str(e))
