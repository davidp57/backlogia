# test_status_sync.py
# Unit tests for game status tracking service

import unittest
from unittest.mock import Mock, patch
import sqlite3

from web.services.status_sync import (
    SteamStatusDetector,
    EpicStatusDetector,
    GOGStatusDetector,
    sync_game_status,
    sync_all_statuses,
    track_update_timestamp,
    get_status_stats
)


class TestSteamStatusDetector(unittest.TestCase):
    """Test Steam status detection."""
    
    @patch('web.services.status_sync.requests.get')
    def test_detect_early_access(self, mock_get):
        """Test detection of Early Access games."""
        mock_response = Mock()
        mock_response.json.return_value = {
            '440': {
                'success': True,
                'data': {
                    'categories': [
                        {'id': 29, 'description': 'Early Access'}
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        status, version = SteamStatusDetector.get_status('440')
        
        self.assertEqual(status, 'early_access')
        self.assertIsNone(version)
    
    @patch('web.services.status_sync.requests.get')
    def test_detect_released(self, mock_get):
        """Test detection of released games."""
        mock_response = Mock()
        mock_response.json.return_value = {
            '440': {
                'success': True,
                'data': {
                    'categories': [
                        {'id': 1, 'description': 'Multi-player'}
                    ]
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        status, version = SteamStatusDetector.get_status('440')
        
        self.assertEqual(status, 'released')
    
    @patch('web.services.status_sync.requests.get')
    def test_api_error(self, mock_get):
        """Test handling of API errors."""
        mock_get.side_effect = Exception("API Error")
        
        status, version = SteamStatusDetector.get_status('440')
        
        self.assertIsNone(status)
        self.assertIsNone(version)


class TestEpicStatusDetector(unittest.TestCase):
    """Test Epic status detection."""
    
    def test_detect_early_access_from_metadata(self):
        """Test detection from Epic metadata."""
        metadata = {
            'customAttributes': {
                'EarlyAccess': {'value': 'true'}
            }
        }
        
        status, version = EpicStatusDetector.get_status_from_metadata(metadata)
        
        self.assertEqual(status, 'early_access')
    
    def test_detect_released(self):
        """Test detection of released games."""
        metadata = {
            'customAttributes': {}
        }
        
        status, version = EpicStatusDetector.get_status_from_metadata(metadata)
        
        self.assertEqual(status, 'released')
    
    def test_invalid_metadata(self):
        """Test handling of invalid metadata."""
        status, version = EpicStatusDetector.get_status_from_metadata(None)
        
        self.assertIsNone(status)


class TestGOGStatusDetector(unittest.TestCase):
    """Test GOG status detection (placeholder)."""
    
    def test_fallback_to_igdb(self):
        """Test IGDB fallback for GOG."""
        status, version = GOGStatusDetector.get_status_from_igdb(None)
        
        # Currently returns None as IGDB integration is not implemented
        self.assertIsNone(status)


class TestSyncGameStatus(unittest.TestCase):
    """Test syncing status for individual games."""
    
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
                extra_data TEXT,
                igdb_id INTEGER,
                development_status TEXT,
                game_version TEXT,
                status_last_synced TEXT
            )
        """)
        
        # Insert test games
        cursor.execute("""
            INSERT INTO games (id, name, store, store_id)
            VALUES (1, 'Steam Game', 'steam', '440')
        """)
        cursor.execute("""
            INSERT INTO games (id, name, store, store_id, extra_data)
            VALUES (2, 'Epic Game', 'epic', 'epicid', '{"customAttributes": {}}')
        """)
        cursor.execute("""
            INSERT INTO games (id, name, store, store_id)
            VALUES (3, 'GOG Game', 'gog', 'gogid')
        """)
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    @patch('web.services.status_sync.SteamStatusDetector.get_status')
    def test_sync_steam_game(self, mock_get_status):
        """Test syncing status for Steam game."""
        mock_get_status.return_value = ('early_access', None)
        
        result = sync_game_status(self.conn, 1)
        
        self.assertTrue(result)
        cursor = self.conn.cursor()
        cursor.execute("SELECT development_status FROM games WHERE id = 1")
        status = cursor.fetchone()[0]
        self.assertEqual(status, 'early_access')
    
    @patch('web.services.status_sync.EpicStatusDetector.get_status_from_metadata')
    def test_sync_epic_game(self, mock_get_status):
        """Test syncing status for Epic game."""
        mock_get_status.return_value = ('released', None)
        
        result = sync_game_status(self.conn, 2)
        
        self.assertTrue(result)
    
    def test_sync_nonexistent_game(self):
        """Test syncing non-existent game."""
        result = sync_game_status(self.conn, 999)
        
        self.assertFalse(result)


class TestSyncAllStatuses(unittest.TestCase):
    """Test batch status syncing."""
    
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
                development_status TEXT,
                status_last_synced TEXT
            )
        """)
        
        cursor.execute("INSERT INTO games (id, name, store, store_id) VALUES (1, 'Game 1', 'steam', '440')")
        cursor.execute("INSERT INTO games (id, name, store, store_id) VALUES (2, 'Game 2', 'steam', '570')")
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    @patch('web.services.status_sync.sync_game_status')
    def test_sync_all(self, mock_sync):
        """Test syncing all games."""
        mock_sync.return_value = True
        
        synced, failed = sync_all_statuses(self.conn, store=None, force=True)
        
        self.assertEqual(synced, 2)
        self.assertEqual(failed, 0)
    
    @patch('web.services.status_sync.sync_game_status')
    def test_sync_filtered_by_store(self, mock_sync):
        """Test syncing filtered by store."""
        mock_sync.return_value = True
        
        synced, failed = sync_all_statuses(self.conn, store='steam', force=True)
        
        self.assertEqual(synced, 2)


class TestTrackUpdateTimestamp(unittest.TestCase):
    """Test update timestamp tracking."""
    
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                name TEXT,
                store TEXT,
                last_modified TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE game_depot_updates (
                id INTEGER PRIMARY KEY,
                game_id INTEGER,
                update_timestamp TEXT,
                fetched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(id)
            )
        """)
        
        cursor.execute("INSERT INTO games (id, name, store) VALUES (1, 'Game', 'steam')")
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    def test_first_sync_no_update_record(self):
        """Test first sync doesn't create update record."""
        store_data = {'last_modified': '2026-01-01T00:00:00'}
        
        result = track_update_timestamp(self.conn, 1, 'steam', store_data)
        
        self.assertFalse(result)
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM game_depot_updates")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 0)
    
    def test_detect_update(self):
        """Test detection of game update."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE games SET last_modified = '2026-01-01T00:00:00' WHERE id = 1")
        self.conn.commit()
        
        store_data = {'last_modified': '2026-01-02T00:00:00'}
        
        result = track_update_timestamp(self.conn, 1, 'steam', store_data)
        
        self.assertTrue(result)
        cursor.execute("SELECT COUNT(*) FROM game_depot_updates WHERE game_id = 1")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 1)
    
    def test_no_update_same_timestamp(self):
        """Test that same timestamp doesn't create record."""
        timestamp = '2026-01-01T00:00:00'
        cursor = self.conn.cursor()
        cursor.execute("UPDATE games SET last_modified = ? WHERE id = 1", (timestamp,))
        self.conn.commit()
        
        store_data = {'last_modified': timestamp}
        
        result = track_update_timestamp(self.conn, 1, 'steam', store_data)
        
        self.assertFalse(result)


class TestGetStatusStats(unittest.TestCase):
    """Test status statistics."""
    
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE games (
                id INTEGER PRIMARY KEY,
                development_status TEXT,
                status_last_synced TEXT
            )
        """)
        
        cursor.execute("INSERT INTO games (id, development_status) VALUES (1, 'early_access')")
        cursor.execute("INSERT INTO games (id, development_status) VALUES (2, 'early_access')")
        cursor.execute("INSERT INTO games (id, development_status) VALUES (3, 'released')")
        cursor.execute("INSERT INTO games (id) VALUES (4)")
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    def test_get_stats(self):
        """Test getting status statistics."""
        stats = get_status_stats(self.conn)
        
        self.assertEqual(stats['games_with_status'], 3)
        self.assertEqual(stats['status_counts']['early_access'], 2)
        self.assertEqual(stats['status_counts']['released'], 1)


if __name__ == '__main__':
    unittest.main()
