# test_news_sync.py
# Unit tests for Steam News sync service

import unittest
from unittest.mock import Mock, patch
import sqlite3

from web.services.news_sync import NewsClient, sync_news, sync_game_news, get_news_stats


class TestNewsClient(unittest.TestCase):
    """Test the NewsClient class."""
    
    def setUp(self):
        self.client = NewsClient()
    
    def test_rate_limiting_initialization(self):
        """Test that rate limiter initializes correctly."""
        self.assertEqual(len(self.client.request_times), 0)
        self.assertEqual(NewsClient.RATE_LIMIT_REQUESTS, 200)
        self.assertEqual(NewsClient.RATE_LIMIT_WINDOW, 300)
    
    @patch('web.services.news_sync.requests.get')
    def test_fetch_news_success(self, mock_get):
        """Test successful news fetch from Steam API."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'appnews': {
                'newsitems': [
                    {
                        'gid': '123',
                        'title': 'Test Update',
                        'contents': 'Test content',
                        'author': 'Test Author',
                        'url': 'http://test.com',
                        'date': 1234567890
                    }
                ]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.client.fetch_news_for_game(440, count=10)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'Test Update')
        self.assertEqual(result[0]['author'], 'Test Author')
    
    @patch('web.services.news_sync.requests.get')
    def test_fetch_news_api_error(self, mock_get):
        """Test handling of API errors."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        result = self.client.fetch_news_for_game(440)
        
        self.assertIsNone(result)
    
    @patch('web.services.news_sync.requests.get')
    def test_fetch_news_empty_response(self, mock_get):
        """Test handling of empty API response."""
        mock_response = Mock()
        mock_response.json.return_value = {'appnews': {}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = self.client.fetch_news_for_game(440)
        
        self.assertEqual(result, [])


class TestNewsSync(unittest.TestCase):
    """Test news sync functions."""
    
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Create schema
        cursor.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                name TEXT,
                store TEXT,
                store_id TEXT,
                news_last_checked TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE game_news (
                id INTEGER PRIMARY KEY,
                game_id INTEGER,
                title TEXT,
                content TEXT,
                author TEXT,
                url TEXT UNIQUE,
                published_at TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id)
            )
        """)
        
        # Insert test games
        cursor.execute("INSERT INTO games (id, name, store, store_id) VALUES (1, 'Test Game', 'steam', '440')")
        cursor.execute("INSERT INTO games (id, name, store, store_id) VALUES (2, 'Epic Game', 'epic', 'epicid')")
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    @patch('web.services.news_sync.NewsClient.fetch_news_for_game')
    def test_sync_game_news(self, mock_fetch):
        """Test syncing news for a single game."""
        mock_fetch.return_value = [
            {
                'title': 'Update 1',
                'contents': 'Content 1',
                'author': 'Author',
                'url': 'http://test.com/1',
                'date': 1234567890
            }
        ]
        
        result = sync_game_news(self.conn, 1, max_items=10)
        
        self.assertTrue(result)
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM game_news WHERE game_id = 1")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
    
    def test_sync_game_news_nonexistent_game(self):
        """Test syncing news for non-existent game."""
        result = sync_game_news(self.conn, 999)
        
        self.assertFalse(result)
    
    def test_sync_game_news_non_steam(self):
        """Test syncing news for non-Steam game (should skip)."""
        result = sync_game_news(self.conn, 2)
        
        self.assertFalse(result)
    
    @patch('web.services.news_sync.sync_game_news')
    def test_sync_news_all_games(self, mock_sync):
        """Test syncing news for all games."""
        mock_sync.return_value = True
        
        synced, failed = sync_news(self.conn, store='steam', force=False)
        
        self.assertEqual(synced, 1)  # Only 1 Steam game
        self.assertEqual(failed, 0)
    
    def test_get_news_stats(self):
        """Test getting news statistics."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO game_news (game_id, title, content, url, published_at)
            VALUES (1, 'Test', 'Content', 'http://test.com', '2026-01-01T00:00:00')
        """)
        self.conn.commit()
        
        stats = get_news_stats(self.conn)
        
        self.assertEqual(stats['total_articles'], 1)
        self.assertEqual(stats['games_with_news'], 1)
        self.assertIsNotNone(stats['last_fetched'])


class TestNewsCaching(unittest.TestCase):
    """Test news caching logic."""
    
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                name TEXT,
                store TEXT,
                store_id TEXT,
                news_last_checked TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE game_news (
                id INTEGER PRIMARY KEY,
                game_id INTEGER,
                title TEXT,
                content TEXT,
                url TEXT UNIQUE,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("INSERT INTO games (id, name, store, store_id) VALUES (1, 'Game', 'steam', '440')")
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    def test_cache_skip_recent_fetch(self):
        """Test that recently fetched news is skipped."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE games SET news_last_checked = datetime('now')
            WHERE id = 1
        """)
        self.conn.commit()
        
        from web.services.news_sync import _should_skip_cache
        should_skip = _should_skip_cache(self.conn, 1, cache_hours=24)
        
        self.assertTrue(should_skip)
    
    def test_cache_allow_old_fetch(self):
        """Test that old news can be re-fetched."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE games SET news_last_checked = datetime('now', '-25 hours')
            WHERE id = 1
        """)
        self.conn.commit()
        
        from web.services.news_sync import _should_skip_cache
        should_skip = _should_skip_cache(self.conn, 1, cache_hours=24)
        
        self.assertFalse(should_skip)


if __name__ == '__main__':
    unittest.main()
