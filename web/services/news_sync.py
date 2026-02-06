# news_sync.py
# Fetches news articles from Steam News API for games in the library

import sqlite3
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta


class NewsClient:
    """Client for fetching news from Steam News API."""
    
    BASE_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"
    RATE_LIMIT_REQUESTS = 200
    RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds
    
    def __init__(self):
        self.request_times = []
        self.lock = threading.Lock()
    
    def _wait_for_rate_limit(self):
        """Enforce rate limiting: 200 requests per 5 minutes."""
        with self.lock:
            now = time.time()
            # Remove timestamps older than 5 minutes
            self.request_times = [t for t in self.request_times if now - t < self.RATE_LIMIT_WINDOW]
            
            if len(self.request_times) >= self.RATE_LIMIT_REQUESTS:
                # Wait until the oldest request is outside the window
                sleep_time = self.RATE_LIMIT_WINDOW - (now - self.request_times[0]) + 1
                if sleep_time > 0:
                    print(f"[NEWS] Rate limit reached, waiting {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                    now = time.time()
                    self.request_times = [t for t in self.request_times if now - t < self.RATE_LIMIT_WINDOW]
            
            # Add small delay between requests to avoid hitting Steam's rate limit
            if self.request_times:
                time_since_last = now - self.request_times[-1]
                if time_since_last < 0.5:  # At least 500ms between requests
                    time.sleep(0.5 - time_since_last)
            
            self.request_times.append(time.time())
    
    def fetch_news_for_game(self, appid, count=10, max_retries=5):
        """
        Fetch news articles for a Steam game by appid.
        
        Args:
            appid: Steam application ID
            count: Maximum number of articles to fetch (default 10)
            max_retries: Maximum number of retry attempts for rate limit errors (default 5)
        
        Returns:
            List of news article dicts, or None on error
        """
        import random
        
        params = {
            'appid': appid,
            'count': count,
            'format': 'json'
        }
        
        headers = {
            'User-Agent': 'Backlogia/1.0 (Game Library Manager; +https://github.com/sam1am/backlogia)'
        }
        
        for attempt in range(max_retries):
            self._wait_for_rate_limit()
            
            try:
                response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'appnews' in data and 'newsitems' in data['appnews']:
                    return data['appnews']['newsitems']
                return []
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403 and attempt < max_retries - 1:
                    # Rate limited by Steam, wait with aggressive exponential backoff + jitter
                    base_wait = 2 ** (attempt + 1)  # 2s, 4s, 8s, 16s, 32s
                    jitter = random.uniform(0, 0.3 * base_wait)
                    wait_time = base_wait + jitter
                    print(f"[NEWS] Rate limited for appid {appid}, waiting {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                print(f"[NEWS] Error fetching news for appid {appid}: {e}")
                return None
            except requests.exceptions.RequestException as e:
                print(f"[NEWS] Error fetching news for appid {appid}: {e}")
                return None
            except Exception as e:
                print(f"[NEWS] Unexpected error for appid {appid}: {e}")
                return None
        
        # All retries exhausted
        print(f"[NEWS] Failed to fetch news for appid {appid} after {max_retries} attempts")
        return None


def _should_skip_cache(conn, game_id, cache_hours=24):
    """Check if news for a game was checked recently (within cache_hours)."""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT news_last_checked FROM games WHERE id = ?
        """, (game_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            last_checked = datetime.fromisoformat(result[0])
            time_since = datetime.now() - last_checked
            return time_since < timedelta(hours=cache_hours)
    except sqlite3.OperationalError as e:
        # Column doesn't exist yet (migration in progress), don't skip
        if "no such column" in str(e).lower():
            return False
        raise
    
    return False


def _store_news_articles(conn, game_id, articles):
    """Store news articles in database, updating existing ones by URL."""
    if not articles:
        return 0
    
    cursor = conn.cursor()
    stored_count = 0
    
    for article in articles:
        title = article.get('title')
        contents = article.get('contents')
        author = article.get('author')
        url = article.get('url')
        date = article.get('date')
        
        # Convert Unix timestamp to ISO format
        published_at = None
        if date:
            try:
                published_at = datetime.fromtimestamp(date).isoformat()
            except (ValueError, TypeError):
                pass
        
        try:
            # Use URL as unique identifier, update if exists
            cursor.execute("""
                INSERT INTO game_news (game_id, title, content, author, url, published_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    author = excluded.author,
                    published_at = excluded.published_at,
                    fetched_at = CURRENT_TIMESTAMP
            """, (game_id, title, contents, author, url, published_at))
            stored_count += 1
        except sqlite3.IntegrityError:
            # URL constraint violation, skip
            continue
        except Exception as e:
            print(f"[NEWS] Error storing article {url}: {e}")
            continue
    
    conn.commit()
    return stored_count


def sync_game_news(conn, game_id, max_items=10):
    """
    Sync news for a single game.
    
    Args:
        conn: Database connection
        game_id: Game ID to sync news for
        max_items: Maximum number of articles to fetch
    
    Returns:
        Number of articles stored, or None on error
    """
    cursor = conn.cursor()
    
    # Get Steam store_id for this game
    cursor.execute("""
        SELECT store_id, name FROM games 
        WHERE id = ? AND store = 'steam' AND store_id IS NOT NULL
    """, (game_id,))
    result = cursor.fetchone()
    
    if not result:
        return None  # Not a Steam game or no store_id
    
    store_id, name = result
    client = NewsClient()
    articles = client.fetch_news_for_game(store_id, count=max_items)
    
    if articles is None:
        return None  # Error fetching
    
    return _store_news_articles(conn, game_id, articles)


def _process_single_game(client, game_id, store_id, name, max_items):
    """Process a single game for news sync (for parallel execution)."""
    try:
        articles = client.fetch_news_for_game(store_id, count=max_items)
        return (game_id, store_id, name, articles)
    except Exception as e:
        print(f"[NEWS] Error processing {name}: {e}")
        return (game_id, store_id, name, None)


def sync_news(conn, store='steam', force=False, max_items=10, max_workers=2, progress_callback=None):
    """
    Sync news for all games from specified store.
    
    Args:
        conn: Database connection
        store: Store to sync ('steam' only supported currently)
        force: If True, fetch news for all games; if False, skip recently fetched (24h cache)
        max_items: Maximum articles per game
        max_workers: Number of parallel workers (default 2, reduced to avoid rate limits)
        progress_callback: Optional callback function(current, total, message) for progress updates
    
    Returns:
        Tuple of (fetched_count, failed_count)
    """
    if store != 'steam':
        print(f"[NEWS] Only Steam is supported for news sync, got: {store}")
        return (0, 0)
    
    cursor = conn.cursor()
    
    # Get all Steam games
    cursor.execute("""
        SELECT id, store_id, name FROM games 
        WHERE store = 'steam' AND store_id IS NOT NULL
        ORDER BY name
    """)
    games = cursor.fetchall()
    
    if not games:
        print("[NEWS] No Steam games found")
        return (0, 0)
    
    # Filter by cache if not force
    if not force:
        games_to_process = []
        for game_id, store_id, name in games:
            if not _should_skip_cache(conn, game_id, cache_hours=24):
                games_to_process.append((game_id, store_id, name))
        games = games_to_process
    
    total = len(games)
    if total == 0:
        print("[NEWS] No games need news sync (all recently fetched)")
        return (0, 0)
    
    print(f"[NEWS] Syncing news for {total} Steam games...")
    
    client = NewsClient()
    fetched = 0
    failed = 0
    completed = 0
    
    # Process games in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_game = {
            executor.submit(_process_single_game, client, game_id, store_id, name, max_items): (game_id, store_id, name)
            for game_id, store_id, name in games
        }
        
        # Process results as they complete
        for future in as_completed(future_to_game):
            game_id, store_id, name = future_to_game[future]
            completed += 1
            
            # Report progress
            if progress_callback:
                progress_callback(completed, total, f"Processing: {name[:50]}...")
            
            try:
                result_game_id, result_store_id, result_name, articles = future.result()
                
                if articles is None:
                    failed += 1
                    print(f"[NEWS] [{completed}/{total}] Failed: {result_name}")
                elif len(articles) == 0:
                    print(f"[NEWS] [{completed}/{total}] No news: {result_name}")
                else:
                    stored = _store_news_articles(conn, result_game_id, articles)
                    fetched += 1
                    print(f"[NEWS] [{completed}/{total}] {result_name}: {stored} articles")
            except Exception as e:
                failed += 1
                print(f"[NEWS] [{completed}/{total}] Exception for {name}: {e}")
    
    print(f"[NEWS] Sync complete: {fetched} games fetched, {failed} failed")
    return (fetched, failed)


def get_news_stats(conn):
    """Get statistics about news sync."""
    cursor = conn.cursor()
    
    # Total articles
    cursor.execute("SELECT COUNT(*) FROM game_news")
    total_articles = cursor.fetchone()[0]
    
    # Games with news
    cursor.execute("SELECT COUNT(DISTINCT game_id) FROM game_news")
    games_with_news = cursor.fetchone()[0]
    
    # Most recent fetch
    cursor.execute("SELECT MAX(fetched_at) FROM game_news")
    last_fetch = cursor.fetchone()[0]
    
    return {
        'total_articles': total_articles,
        'games_with_news': games_with_news,
        'last_fetched': last_fetch
    }


def sync_news_job(job_id: str, force: bool = False, max_items: int = 10):
    """
    Job function to sync news for all Steam games sequentially.
    Uses job system for progress tracking and handles rate limiting gracefully.
    
    Args:
        job_id: Job ID for progress tracking
        force: If True, sync all games; if False, skip recently synced (24h cache)
        max_items: Maximum articles per game
    """
    from ..config import DATABASE_PATH
    from .jobs import update_job_progress, complete_job, fail_job, is_job_cancelled
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all Steam games
        cursor.execute("""
            SELECT id, store_id, name FROM games 
            WHERE store = 'steam' AND store_id IS NOT NULL
            ORDER BY name
        """)
        games = cursor.fetchall()
        
        if not games:
            complete_job(job_id, "0", "No Steam games found")
            conn.close()
            return
        
        # Filter by cache if not force
        if not force:
            games_to_process = []
            for game_id, store_id, name in games:
                if not _should_skip_cache(conn, game_id, cache_hours=24):
                    games_to_process.append((game_id, store_id, name))
            games = games_to_process
        
        total = len(games)
        if total == 0:
            complete_job(job_id, "0", "All games recently synced (cache valid)")
            conn.close()
            return
        
        print(f"[NEWS JOB {job_id}] Syncing news for {total} Steam games...")
        update_job_progress(job_id, 0, total, f"Starting sync for {total} games")
        
        client = NewsClient()
        fetched = 0
        failed = 0
        
        # Process games sequentially to avoid rate limit issues
        for idx, (game_id, store_id, name) in enumerate(games, 1):
            # Check if job has been cancelled
            if is_job_cancelled(job_id):
                conn.close()
                print(f"[NEWS JOB {job_id}] Cancelled by user at {idx}/{total}")
                return
            
            try:
                # Update progress
                update_job_progress(job_id, idx - 1, total, f"Processing: {name[:50]}...")
                
                # Fetch and store news
                articles = client.fetch_news_for_game(store_id, count=max_items)
                
                if articles is None:
                    failed += 1
                    print(f"[NEWS JOB {job_id}] [{idx}/{total}] Failed: {name}")
                    # Still mark as checked to avoid immediate retry
                    try:
                        cursor.execute("UPDATE games SET news_last_checked = ? WHERE id = ?",
                                       (datetime.now().isoformat(), game_id))
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column doesn't exist yet
                elif len(articles) == 0:
                    print(f"[NEWS JOB {job_id}] [{idx}/{total}] No news: {name}")
                    # Mark as checked even with no articles
                    try:
                        cursor.execute("UPDATE games SET news_last_checked = ? WHERE id = ?",
                                       (datetime.now().isoformat(), game_id))
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column doesn't exist yet
                else:
                    stored = _store_news_articles(conn, game_id, articles)
                    fetched += 1
                    print(f"[NEWS JOB {job_id}] [{idx}/{total}] {name}: {stored} articles")
                    # Mark as checked after storing articles
                    try:
                        cursor.execute("UPDATE games SET news_last_checked = ? WHERE id = ?",
                                       (datetime.now().isoformat(), game_id))
                        conn.commit()
                    except sqlite3.OperationalError:
                        pass  # Column doesn't exist yet
                    
            except Exception as e:
                failed += 1
                print(f"[NEWS JOB {job_id}] [{idx}/{total}] Exception for {name}: {e}")
                # Mark as checked even on exception to avoid getting stuck
                try:
                    cursor.execute("UPDATE games SET news_last_checked = ? WHERE id = ?",
                                   (datetime.now().isoformat(), game_id))
                    conn.commit()
                except Exception:
                    pass
        
        conn.close()
        
        # Complete job
        result_msg = f"{fetched} games synced, {failed} failed"
        complete_job(job_id, str(fetched), result_msg)
        print(f"[NEWS JOB {job_id}] Complete: {result_msg}")
        
    except Exception as e:
        print(f"[NEWS JOB {job_id}] Fatal error: {e}")
        fail_job(job_id, str(e))
