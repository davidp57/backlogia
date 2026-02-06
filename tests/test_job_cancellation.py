# tests/test_job_cancellation.py
# Test job cancellation functionality

import sqlite3
import time
from unittest.mock import patch, Mock

import pytest

from web.services.jobs import (
    JobType, JobStatus, create_job, cancel_job, is_job_cancelled,
    get_job, update_job_progress, ensure_jobs_table
)
from web.config import DATABASE_PATH


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Create a fresh test database."""
    db_path = tmp_path / "test_job_cancel.db"
    monkeypatch.setattr("web.services.jobs.DATABASE_PATH", str(db_path))
    monkeypatch.setattr("web.config.DATABASE_PATH", str(db_path))
    
    # Create tables
    ensure_jobs_table()
    
    # Create games table for job functions
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            name TEXT,
            store TEXT,
            store_id TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            title TEXT,
            url TEXT,
            date INTEGER,
            FOREIGN KEY (game_id) REFERENCES games(id),
            UNIQUE(game_id, url)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_depot_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id INTEGER NOT NULL,
            last_checked TIMESTAMP,
            status TEXT,
            FOREIGN KEY (game_id) REFERENCES games(id)
        )
    """)
    # Create 100 test games for timing tests
    for i in range(1, 101):
        cursor.execute("""
            INSERT INTO games (name, store, store_id)
            VALUES (?, 'steam', ?)
        """, (f"Test Game {i}", str(10000 + i)))
    conn.commit()
    conn.close()
    
    yield str(db_path)
    
    # Clear cancelled jobs set after test
    from web.services.jobs import _cancelled_jobs
    _cancelled_jobs.clear()


class TestJobCancellation:
    """Test job cancellation functionality."""
    
    def test_cancel_pending_job(self, fresh_db):
        """Test cancelling a pending job."""
        job_id = create_job(JobType.NEWS_SYNC, "Test job")
        
        job = get_job(job_id)
        assert job['status'] == JobStatus.PENDING.value
        assert job['cancelled'] == 0
        
        # Cancel the job
        result = cancel_job(job_id)
        assert result is True
        
        # Verify job is cancelled
        job = get_job(job_id)
        assert job['status'] == JobStatus.FAILED.value
        assert job['cancelled'] == 1
        assert job['error'] == "Cancelled by user"
        assert job['completed_at'] is not None
        
    def test_cancel_running_job(self, fresh_db):
        """Test cancelling a running job."""
        job_id = create_job(JobType.NEWS_SYNC, "Test job")
        update_job_progress(job_id, 5, 10, "Processing...")
        
        job = get_job(job_id)
        assert job['status'] == JobStatus.RUNNING.value
        
        # Cancel the job
        result = cancel_job(job_id)
        assert result is True
        
        # Verify job is cancelled
        job = get_job(job_id)
        assert job['status'] == JobStatus.FAILED.value
        assert job['cancelled'] == 1
        
    def test_cannot_cancel_completed_job(self, fresh_db):
        """Test that completed jobs cannot be cancelled."""
        job_id = create_job(JobType.NEWS_SYNC, "Test job")
        
        # Mark as completed
        conn = sqlite3.connect(fresh_db)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs SET status = ?, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (JobStatus.COMPLETED.value, job_id))
        conn.commit()
        conn.close()
        
        # Try to cancel
        result = cancel_job(job_id)
        assert result is False
        
        # Job should still be completed
        job = get_job(job_id)
        assert job['status'] == JobStatus.COMPLETED.value
        assert job['cancelled'] == 0
        
    def test_is_job_cancelled_check(self, fresh_db):
        """Test checking if a job is cancelled."""
        job_id = create_job(JobType.NEWS_SYNC, "Test job")
        
        # Initially not cancelled
        assert is_job_cancelled(job_id) is False
        
        # Cancel the job
        cancel_job(job_id)
        
        # Should now be cancelled
        assert is_job_cancelled(job_id) is True
        
    def test_news_sync_respects_cancellation(self, fresh_db):
        """Test that news sync job stops when cancelled."""
        from web.services.news_sync import sync_news_job
        
        job_id = create_job(JobType.NEWS_SYNC, "Test sync")
        
        # Mock NewsClient with artificial delay to prevent real API calls
        with patch('web.services.news_sync.NewsClient') as MockClient:
            mock_client = Mock()
            
            # Add delay to simulate real processing
            def slow_fetch(*args, **kwargs):
                time.sleep(0.05)  # 50ms per game
                return [
                    {"title": "News 1", "url": "http://example.com/1", "date": 1234567890}
                ]
            
            mock_client.fetch_news_for_game.side_effect = slow_fetch
            MockClient.return_value = mock_client
            
            # Start the job in a thread and cancel it after a short delay
            import threading
            
            def run_sync():
                sync_news_job(job_id, force=True, max_items=5)
            
            thread = threading.Thread(target=run_sync, daemon=True)
            thread.start()
            
            # Give it time to process a few games
            time.sleep(0.3)
            
            # Cancel the job
            cancel_job(job_id)
            
            # Wait for thread to finish
            thread.join(timeout=2)
            
            # Job should be cancelled (not completed)
            job = get_job(job_id)
            assert job['cancelled'] == 1
            
            # Should have processed some but not all games (100 total)
            assert job['progress'] > 0
            assert job['progress'] < 100
            
    def test_status_sync_respects_cancellation(self, fresh_db):
        """Test that status sync job stops when cancelled."""
        from web.services.status_sync import sync_all_statuses_job
        
        job_id = create_job(JobType.STATUS_SYNC, "Test status sync")
        
        # Mock the sync functions with delay to prevent real API calls
        with patch('web.services.status_sync.sync_game_status') as mock_sync:
            def slow_sync(*args, **kwargs):
                time.sleep(0.05)  # 50ms per game
                return True
            
            mock_sync.side_effect = slow_sync
            
            import threading
            
            def run_sync():
                sync_all_statuses_job(job_id, store='steam', force=True)
            
            thread = threading.Thread(target=run_sync, daemon=True)
            thread.start()
            
            # Give it time to process a few games
            time.sleep(0.3)
            
            # Cancel the job
            cancel_job(job_id)
            
            # Wait for thread to finish
            thread.join(timeout=2)
            
            # Job should be cancelled
            job = get_job(job_id)
            assert job['cancelled'] == 1
            
            # Should have processed some but not all games (100 total)
            assert job['progress'] > 0
            assert job['progress'] < 100
            
    def test_cancel_multiple_jobs(self, fresh_db):
        """Test cancelling multiple jobs."""
        job_ids = []
        
        # Create 3 jobs
        for i in range(3):
            job_id = create_job(JobType.NEWS_SYNC, f"Job {i}")
            update_job_progress(job_id, i, 10, f"Processing {i}")
            job_ids.append(job_id)
        
        # Cancel all jobs
        for job_id in job_ids:
            result = cancel_job(job_id)
            assert result is True
        
        # Verify all are cancelled
        for job_id in job_ids:
            job = get_job(job_id)
            assert job['cancelled'] == 1
            assert job['status'] == JobStatus.FAILED.value
            assert is_job_cancelled(job_id) is True
            
    def test_cancelled_column_exists(self, fresh_db):
        """Test that cancelled column was added to jobs table."""
        conn = sqlite3.connect(fresh_db)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [row[1] for row in cursor.fetchall()]
        
        assert 'cancelled' in columns
        
        conn.close()
