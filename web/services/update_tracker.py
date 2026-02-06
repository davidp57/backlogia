# update_tracker.py
# Tracks game updates by detecting changes in last_modified timestamps
# and development status across different stores

import sqlite3
import requests
import time
from datetime import datetime
from typing import Optional, Dict


class UpdateTracker:
    """Main service for tracking game updates."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.steam_tracker = SteamUpdateTracker()
        self.epic_tracker = EpicUpdateTracker()
    
    def check_updates_for_game(self, game_id: int, store: str, store_id: str) -> bool:
        """
        Check if a game has updates and record them.
        
        Args:
            game_id: Internal game ID
            store: Store name (steam, epic, gog, etc.)
            store_id: Store-specific identifier (appid for Steam, namespace for Epic, etc.)
            
        Returns:
            True if update was detected and recorded
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current game data from DB
        cursor.execute("""
            SELECT last_modified, development_status
            FROM games
            WHERE id = ?
        """, (game_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        db_last_modified, db_status = row
        
        # Fetch latest metadata from store
        if store == 'steam':
            metadata = self.steam_tracker.fetch_metadata(store_id)
        elif store == 'epic':
            metadata = self.epic_tracker.fetch_metadata(store_id)
        else:
            conn.close()
            return False  # Unsupported store for now
        
        if not metadata:
            conn.close()
            return False
        
        # Check for changes
        update_detected = False
        change_type = None
        
        new_last_modified = metadata.get('last_modified')
        new_status = metadata.get('development_status')
        
        # Detect last_modified change (version update)
        if new_last_modified:
            # Case 1: DB has no last_modified but store has one -> initial population
            if not db_last_modified:
                update_detected = True
                change_type = 'initial_version'
                
                # Update game record
                cursor.execute("""
                    UPDATE games
                    SET last_modified = ?
                    WHERE id = ?
                """, (new_last_modified, game_id))
                
                # Record in update history as initial entry
                cursor.execute("""
                    INSERT INTO game_depot_updates 
                    (game_id, depot_id, manifest_id, update_timestamp, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    game_id,
                    f"{store}:{store_id}",
                    'initial_version',
                    new_last_modified,
                    datetime.now().isoformat()
                ))
            
            # Case 2: DB has older last_modified -> real update detected
            elif new_last_modified != db_last_modified:
                update_detected = True
                change_type = 'version_update'
                
                # Update game record
                cursor.execute("""
                    UPDATE games
                    SET last_modified = ?
                    WHERE id = ?
                """, (new_last_modified, game_id))
                
                # Record in update history
                cursor.execute("""
                    INSERT INTO game_depot_updates 
                    (game_id, depot_id, manifest_id, update_timestamp, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    game_id,
                    f"{store}:{store_id}",
                    'version_update',
                    new_last_modified,
                    datetime.now().isoformat()
                ))
        
        # Detect status change (EA → Released)
        if new_status and new_status != db_status:
            # Only track EA → Released transitions
            if db_status == 'early_access' and new_status == 'released':
                update_detected = True
                change_type = 'ea_release'
                
                # Update game record
                cursor.execute("""
                    UPDATE games
                    SET development_status = ?
                    WHERE id = ?
                """, (new_status, game_id))
                
                # Record in update history
                cursor.execute("""
                    INSERT INTO game_depot_updates 
                    (game_id, depot_id, manifest_id, update_timestamp, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    game_id,
                    f"{store}:{store_id}",
                    'ea_release',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
        
        conn.commit()
        conn.close()
        
        if update_detected:
            print(f"[UPDATE] Detected {change_type} for game {game_id} ({store}:{store_id})")
        
        return update_detected
    
    def sync_all_games(self, limit: Optional[int] = None):
        """
        Sync updates for all games in library.
        
        Args:
            limit: Optional limit on number of games to check (for testing)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all games with store identifiers
        query = """
            SELECT id, store, store_id
            FROM games
            WHERE store_id IS NOT NULL
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        games = cursor.fetchall()
        conn.close()
        
        total_updates = 0
        
        for game_id, store, store_id in games:
            try:
                if self.check_updates_for_game(game_id, store, store_id):
                    total_updates += 1
                
                # Rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                print(f"[UPDATE] Error checking game {game_id}: {e}")
                continue
        
        print(f"[UPDATE] Sync complete. {total_updates} updates detected.")
        return total_updates


class SteamUpdateTracker:
    """Track updates for Steam games."""
    
    APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
    
    def fetch_metadata(self, store_id: str) -> Optional[Dict]:
        """
        Fetch current metadata for a Steam game.
        
        Args:
            store_id: Steam appid
        
        Returns:
            Dict with 'last_modified' and 'development_status' keys, or None
        """
        headers = {
            'User-Agent': 'Backlogia/1.0 (Game Library Manager; +https://github.com/sam1am/backlogia)'
        }
        
        # Retry logic with exponential backoff for rate limiting
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    self.APP_DETAILS_URL,
                    params={'appids': store_id},
                    headers=headers,
                    timeout=10
                )
                
                # Handle 429 rate limiting with backoff
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"[UPDATE] Rate limited for {store_id}, waiting {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"[UPDATE] Rate limit exceeded for {store_id} after {max_retries} attempts")
                        return None
                
                response.raise_for_status()
                data = response.json()
                
                if str(store_id) not in data or not data[str(store_id)].get('success'):
                    return None
                
                app_data = data[str(store_id)]['data']
                
                # Extract last_modified timestamp (Unix timestamp)
                # Note: Steam doesn't always provide this in appdetails
                # We might need to use another method
                last_modified_unix = app_data.get('last_modified')
                last_modified = None
                if last_modified_unix:
                    # Convert Unix timestamp to ISO format
                    last_modified = datetime.fromtimestamp(last_modified_unix).isoformat()
                
                # Check for Early Access (category 29)
                development_status = 'released'
                categories = app_data.get('categories', [])
                for category in categories:
                    if category.get('id') == 29:  # Early Access category
                        development_status = 'early_access'
                        break
                
                return {
                    'last_modified': last_modified,
                    'development_status': development_status
                }
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"[UPDATE] Request error for {store_id}, retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"[UPDATE] Error fetching Steam metadata for {store_id}: {e}")
                    return None
            except Exception as e:
                print(f"[UPDATE] Unexpected error for Steam {store_id}: {e}")
                return None
        
        return None


class EpicUpdateTracker:
    """Track updates for Epic Games."""
    
    def fetch_metadata(self, namespace: str) -> Optional[Dict]:
        """
        Fetch current metadata for an Epic game.
        
        NOTE: This requires authentication with Epic Games API.
        For now, this is a placeholder. Full implementation would require
        integrating with the epic-games-store-api library.
        
        Returns:
            Dict with 'last_modified' and 'development_status' keys, or None
        """
        # TODO: Implement Epic Games metadata fetching
        # This would require:
        # 1. Epic Games API authentication
        # 2. Fetching game metadata from their API
        # 3. Extracting lastModifiedDate and status
        
        # For now, return None (Epic update tracking not yet implemented)
        return None


def sync_updates(db_path: str, limit: Optional[int] = None) -> int:
    """
    Convenience function to sync updates for all games.
    
    Args:
        db_path: Path to SQLite database
        limit: Optional limit on number of games to check
        
    Returns:
        Number of updates detected
    """
    tracker = UpdateTracker(db_path)
    return tracker.sync_all_games(limit=limit)


def sync_updates_job(job_id: str, limit: Optional[int] = None):
    """
    Job function to sync updates for all games.
    Uses job system for progress tracking and cancellation support.
    
    Args:
        job_id: Job ID for progress tracking
        limit: Optional limit on number of games to check
    """
    from ..config import DATABASE_PATH
    from .jobs import update_job_progress, complete_job, fail_job, is_job_cancelled
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all games with store identifiers
        query = """
            SELECT id, store, store_id, name
            FROM games
            WHERE store_id IS NOT NULL
            ORDER BY name
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        games = cursor.fetchall()
        conn.close()
        
        if not games:
            complete_job(job_id, "0", "No games found for update tracking")
            return
        
        total = len(games)
        print(f"[UPDATE JOB {job_id}] Tracking updates for {total} games...")
        update_job_progress(job_id, 0, total, f"Starting update tracking for {total} games")
        
        tracker = UpdateTracker(str(DATABASE_PATH))
        updates_detected = 0
        failed = 0
        
        for i, (game_id, store, store_id, name) in enumerate(games, 1):
            # Check if job was cancelled
            if is_job_cancelled(job_id):
                fail_job(job_id, "Tracking cancelled by user")
                print(f"[UPDATE JOB {job_id}] Cancelled at game {i}/{total}")
                return
            
            try:
                if tracker.check_updates_for_game(game_id, store, store_id):
                    updates_detected += 1
                
                # Update progress every game
                if i % 10 == 0 or i == total:
                    update_job_progress(
                        job_id, 
                        i, 
                        total, 
                        f"Checked {i}/{total} games - {updates_detected} updates found"
                    )
                
                # Rate limiting - Steam API needs ~1.5s between requests
                if store == 'steam':
                    time.sleep(1.5)
                else:
                    time.sleep(0.5)
                
            except Exception as e:
                print(f"[UPDATE JOB {job_id}] Error checking game {game_id} ({name}): {e}")
                failed += 1
                continue
        
        # Complete job
        complete_job(
            job_id, 
            str(updates_detected), 
            f"Found {updates_detected} updates in {total} games ({failed} failed)"
        )
        
        print(f"[UPDATE JOB {job_id}] Complete. {updates_detected} updates detected.")
        
    except Exception as e:
        fail_job(job_id, str(e))
        print(f"[UPDATE JOB {job_id}] Failed: {e}")
        raise
