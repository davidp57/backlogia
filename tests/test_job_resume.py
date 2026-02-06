# tests/test_job_resume.py
# Test automatic job resumption after server restart

import sqlite3
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

from web.services.jobs import (
    JobType, JobStatus, create_job, cleanup_orphaned_jobs,
    get_job, update_job_progress, ensure_jobs_table
)
from web.config import DATABASE_PATH


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Create a fresh test database."""
    db_path = tmp_path / "test_job_resume.db"
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
        INSERT INTO games (name, store, store_id)
        VALUES ('Test Game 1', 'steam', '12345'),
               ('Test Game 2', 'steam', '67890')
    """)
    conn.commit()
    conn.close()
    
    yield str(db_path)


class TestJobResume:
    """Test automatic job resumption after interruption."""
    
    def test_resume_news_sync_job(self, fresh_db):
        """Test that interrupted NEWS_SYNC jobs are resumed on startup."""
        # Create a job and mark it as RUNNING (simulating interruption)
        job_id = create_job(JobType.NEWS_SYNC, "Test news sync")
        update_job_progress(job_id, 5, 10, "Processing games...")
        
        job = get_job(job_id)
        assert job['status'] == JobStatus.RUNNING.value
        
        # Mock the actual job functions to prevent real execution
        with patch('web.services.jobs.run_job_async') as mock_run_async:
            with patch('web.services.news_sync.sync_news_job'):
                # Call cleanup (simulating server restart)
                cleanup_orphaned_jobs()
                
                # Check that run_job_async was called to resume the job
                assert mock_run_async.call_count == 1
                call_args = mock_run_async.call_args
                resumed_job_id = call_args[0][0]
                assert resumed_job_id == job_id
        
        # Job should be reset to PENDING
        job = get_job(job_id)
        assert job['status'] == JobStatus.PENDING.value
        assert 'Resuming' in job['message']
    
    def test_resume_status_sync_job(self, fresh_db):
        """Test that interrupted STATUS_SYNC jobs are resumed on startup."""
        job_id = create_job(JobType.STATUS_SYNC, "Test status sync")
        update_job_progress(job_id, 3, 8, "Checking statuses...")
        
        job = get_job(job_id)
        assert job['status'] == JobStatus.RUNNING.value
        
        with patch('web.services.jobs.run_job_async') as mock_run_async:
            with patch('web.services.status_sync.sync_all_statuses_job'):
                cleanup_orphaned_jobs()
                
                # Should resume STATUS_SYNC
                assert mock_run_async.call_count == 1
        
        job = get_job(job_id)
        assert job['status'] == JobStatus.PENDING.value
    
    def test_fail_non_resumable_jobs(self, fresh_db):
        """Test that non-resumable job types are marked as failed."""
        # Create jobs of different types
        store_job = create_job(JobType.STORE_SYNC, "Test store sync")
        igdb_job = create_job(JobType.IGDB_SYNC, "Test IGDB sync")
        
        # Mark them as running
        update_job_progress(store_job, 1, 5, "Syncing...")
        update_job_progress(igdb_job, 2, 10, "Fetching...")
        
        with patch('web.services.jobs.run_job_async') as mock_run_async:
            cleanup_orphaned_jobs()
            
            # Should NOT resume these types
            assert mock_run_async.call_count == 0
        
        # Jobs should be marked as failed
        store = get_job(store_job)
        igdb = get_job(igdb_job)
        
        assert store['status'] == JobStatus.FAILED.value
        assert 'cannot auto-resume' in store['error']
        
        assert igdb['status'] == JobStatus.FAILED.value
        assert 'cannot auto-resume' in igdb['error']
    
    def test_resume_multiple_jobs(self, fresh_db):
        """Test resuming multiple interrupted jobs."""
        # Create multiple interrupted jobs
        news_job1 = create_job(JobType.NEWS_SYNC, "News 1")
        news_job2 = create_job(JobType.NEWS_SYNC, "News 2")
        status_job = create_job(JobType.STATUS_SYNC, "Status")
        store_job = create_job(JobType.STORE_SYNC, "Store")
        
        # Mark all as running
        for jid in [news_job1, news_job2, status_job, store_job]:
            update_job_progress(jid, 1, 10, "Processing...")
        
        with patch('web.services.jobs.run_job_async') as mock_run_async:
            with patch('web.services.news_sync.sync_news_job'):
                with patch('web.services.status_sync.sync_all_statuses_job'):
                    cleanup_orphaned_jobs()
                    
                    # Should resume 3 jobs (2 NEWS_SYNC + 1 STATUS_SYNC)
                    assert mock_run_async.call_count == 3
        
        # Check statuses
        assert get_job(news_job1)['status'] == JobStatus.PENDING.value
        assert get_job(news_job2)['status'] == JobStatus.PENDING.value
        assert get_job(status_job)['status'] == JobStatus.PENDING.value
        assert get_job(store_job)['status'] == JobStatus.FAILED.value
    
    def test_no_jobs_to_resume(self, fresh_db):
        """Test cleanup when no jobs need resumption."""
        # Create some completed jobs
        job1 = create_job(JobType.NEWS_SYNC, "Already done")
        
        conn = sqlite3.connect(fresh_db)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE jobs SET status = ?, completed_at = ?
            WHERE id = ?
        """, (JobStatus.COMPLETED.value, datetime.now().isoformat(), job1))
        conn.commit()
        conn.close()
        
        with patch('web.services.jobs.run_job_async') as mock_run_async:
            cleanup_orphaned_jobs()
            
            # Should not resume anything
            assert mock_run_async.call_count == 0
    
    def test_resume_uses_cache(self, fresh_db):
        """Verify that resumed jobs use force=False to respect cache."""
        job_id = create_job(JobType.NEWS_SYNC, "Test cache")
        update_job_progress(job_id, 1, 5, "Processing...")
        
        with patch('web.services.jobs.run_job_async') as mock_run_async:
            with patch('web.services.news_sync.sync_news_job') as mock_sync:
                cleanup_orphaned_jobs()
                
                # Check that run_job_async was called
                assert mock_run_async.call_count == 1
                
                # Get the lambda function that was passed
                call_args = mock_run_async.call_args
                job_func = call_args[0][1]
                
                # Execute the lambda to trigger sync_news_job
                job_func(job_id)
                
                # Verify sync_news_job was called with force=False
                mock_sync.assert_called_once()
                args = mock_sync.call_args[0]
                kwargs = mock_sync.call_args[1]
                
                assert args[0] == job_id
                assert kwargs['force'] is False
                assert kwargs['max_items'] == 10
