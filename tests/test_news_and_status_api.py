# test_news_and_status_api.py
# Integration tests for news and status API endpoints

import unittest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

# Mock init_database before importing app
with patch('web.main.init_database'):
    from web.main import app
    from web.dependencies import get_db


class TestNewsSyncAPI(unittest.TestCase):
    """Test /api/sync/news endpoints."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    @patch('web.routes.sync.run_job_async')
    @patch('web.routes.sync.create_job')
    def test_sync_news_new_mode(self, mock_create_job, mock_run_job):
        """Test syncing news with 'new' mode."""
        mock_create_job.return_value = "test-job-123"
        
        response = self.client.post('/api/sync/news/new')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['job_id'], 'test-job-123')
        mock_create_job.assert_called_once()
        mock_run_job.assert_called_once()
    
    @patch('web.routes.sync.run_job_async')
    @patch('web.routes.sync.create_job')
    def test_sync_news_all_mode(self, mock_create_job, mock_run_job):
        """Test syncing news with 'all' mode (force)."""
        mock_create_job.return_value = "test-job-456"
        
        response = self.client.post('/api/sync/news/all')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['job_id'], 'test-job-456')
    
    def test_sync_news_invalid_store(self):
        """Test syncing news for unsupported store."""
        response = self.client.post('/api/sync/news/epic')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not available', data['message'])


class TestStatusSyncAPI(unittest.TestCase):
    """Test /api/sync/status endpoints."""
    
    def setUp(self):
        self.client = TestClient(app)
    
    @patch('web.routes.sync.run_job_async')
    @patch('web.routes.sync.create_job')
    def test_sync_status_new_mode(self, mock_create_job, mock_run_job):
        """Test syncing status with 'new' mode."""
        mock_create_job.return_value = "test-job-789"
        
        response = self.client.post('/api/sync/status/new')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['job_id'], 'test-job-789')
        mock_create_job.assert_called_once()
        mock_run_job.assert_called_once()
    
    @patch('web.routes.sync.run_job_async')
    @patch('web.routes.sync.create_job')
    def test_sync_status_steam_only(self, mock_create_job, mock_run_job):
        """Test syncing status for Steam only."""
        mock_create_job.return_value = "test-job-101"
        
        response = self.client.post('/api/sync/status/steam')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['job_id'], 'test-job-101')
    
    def test_sync_status_invalid_store(self):
        """Test syncing status for unsupported store."""
        response = self.client.post('/api/sync/status/itch')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not available', data['message'])


class TestGameNewsAPI(unittest.TestCase):
    """Test /api/game/{game_id}/news endpoint."""
    
    def setUp(self):
        self.client = TestClient(app)
        # Mock database dependency
        self.mock_conn = Mock()
        self.mock_cursor = Mock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        app.dependency_overrides[get_db] = lambda: self.mock_conn
    
    def tearDown(self):
        # Clean up overrides
        app.dependency_overrides.clear()
    
    def test_get_news_for_steam_game(self):
        """Test getting news for a Steam game."""
        # Mock game exists and is Steam
        self.mock_cursor.fetchone.side_effect = [
            {'id': 1, 'name': 'Test Game', 'store': 'steam'},  # First call for game
        ]
        # Mock news articles
        self.mock_cursor.fetchall.return_value = [
            {
                'title': 'Update 1',
                'content': 'Content 1',
                'author': 'Author',
                'url': 'http://test.com/1',
                'published_at': '2026-01-01T00:00:00',
                'fetched_at': '2026-01-01T01:00:00'
            }
        ]
        
        response = self.client.get('/api/game/1/news')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['game_id'], 1)
        self.assertEqual(len(data['articles']), 1)
        self.assertEqual(data['articles'][0]['title'], 'Update 1')
    
    def test_get_news_for_non_steam_game(self):
        """Test getting news for non-Steam game."""
        self.mock_cursor.fetchone.return_value = {
            'id': 2,
            'name': 'Epic Game',
            'store': 'epic'
        }
        
        response = self.client.get('/api/game/2/news')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['articles']), 0)
        self.assertIn('only available for Steam', data['message'])
    
    def test_get_news_game_not_found(self):
        """Test getting news for non-existent game."""
        self.mock_cursor.fetchone.return_value = None
        
        response = self.client.get('/api/game/999/news')
        
        self.assertEqual(response.status_code, 404)


class TestGameUpdatesAPI(unittest.TestCase):
    """Test /api/game/{game_id}/updates endpoint."""
    
    def setUp(self):
        self.client = TestClient(app)
        # Mock database dependency
        self.mock_conn = Mock()
        self.mock_cursor = Mock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        app.dependency_overrides[get_db] = lambda: self.mock_conn
    
    def tearDown(self):
        # Clean up overrides
        app.dependency_overrides.clear()
    
    def test_get_updates_for_game(self):
        """Test getting update history for a game."""
        # Mock game exists
        self.mock_cursor.fetchone.return_value = {
            'id': 1,
            'name': 'Test Game',
            'store': 'steam',
            'last_modified': '2026-01-05T00:00:00'
        }
        # Mock update history
        self.mock_cursor.fetchall.return_value = [
            {
                'update_timestamp': '2026-01-05T00:00:00',
                'fetched_at': '2026-01-05T01:00:00'
            },
            {
                'update_timestamp': '2026-01-01T00:00:00',
                'fetched_at': '2026-01-01T01:00:00'
            }
        ]
        
        response = self.client.get('/api/game/1/updates')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['game_id'], 1)
        self.assertEqual(len(data['updates']), 2)
        self.assertEqual(data['count'], 2)
    
    def test_get_updates_with_limit(self):
        """Test getting update history with custom limit."""
        self.mock_cursor.fetchone.return_value = {
            'id': 1,
            'name': 'Test Game',
            'store': 'steam',
            'last_modified': '2026-01-05T00:00:00'
        }
        self.mock_cursor.fetchall.return_value = []
        
        response = self.client.get('/api/game/1/updates?limit=5')
        
        self.assertEqual(response.status_code, 200)
    
    def test_get_updates_game_not_found(self):
        """Test getting updates for non-existent game."""
        self.mock_cursor.fetchone.return_value = None
        
        response = self.client.get('/api/game/999/updates')
        
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
