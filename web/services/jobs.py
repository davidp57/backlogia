# services/jobs.py
# Job management service for tracking background sync operations

import sqlite3
import threading
import uuid
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from ..config import DATABASE_PATH


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    STORE_SYNC = "store_sync"
    IGDB_SYNC = "igdb_sync"
    METACRITIC_SYNC = "metacritic_sync"
    PROTONDB_SYNC = "protondb_sync"
    NEWS_SYNC = "news_sync"
    STATUS_SYNC = "status_sync"
    UPDATE_TRACKING = "update_tracking"


# Thread-safe set for tracking cancelled jobs
_cancelled_jobs: set = set()
_cancelled_jobs_lock = threading.Lock()


def ensure_jobs_table():
    """Create jobs table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            progress INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            message TEXT,
            result TEXT,
            error TEXT,
            cancelled BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)
    
    # Add cancelled column to existing tables if it doesn't exist
    try:
        cursor.execute("ALTER TABLE jobs ADD COLUMN cancelled BOOLEAN DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass

    conn.commit()
    conn.close()


def create_job(job_type: JobType, message: str = "") -> str:
    """Create a new job and return its ID."""
    ensure_jobs_table()

    job_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO jobs (id, type, status, message, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (job_id, job_type.value, JobStatus.PENDING.value, message,
          datetime.now().isoformat(), datetime.now().isoformat()))

    conn.commit()
    conn.close()

    return job_id


def update_job_progress(job_id: str, progress: int, total: int, message: str = ""):
    """Update job progress."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET progress = ?, total = ?, message = ?, status = ?, updated_at = ?
        WHERE id = ?
    """, (progress, total, message, JobStatus.RUNNING.value,
          datetime.now().isoformat(), job_id))

    conn.commit()
    conn.close()


def complete_job(job_id: str, result: str, message: str = ""):
    """Mark job as completed."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET status = ?, result = ?, message = ?, progress = total,
            updated_at = ?, completed_at = ?
        WHERE id = ?
    """, (JobStatus.COMPLETED.value, result, message,
          datetime.now().isoformat(), datetime.now().isoformat(), job_id))

    conn.commit()
    conn.close()


def fail_job(job_id: str, error: str):
    """Mark job as failed."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET status = ?, error = ?, updated_at = ?, completed_at = ?
        WHERE id = ?
    """, (JobStatus.FAILED.value, error,
          datetime.now().isoformat(), datetime.now().isoformat(), job_id))

    conn.commit()
    conn.close()


def cancel_job(job_id: str):
    """Cancel a running job."""
    with _cancelled_jobs_lock:
        _cancelled_jobs.add(job_id)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE jobs
        SET status = ?, cancelled = 1, error = ?, updated_at = ?, completed_at = ?
        WHERE id = ? AND status IN (?, ?)
    """, (
        JobStatus.FAILED.value,
        "Cancelled by user",
        datetime.now().isoformat(),
        datetime.now().isoformat(),
        job_id,
        JobStatus.PENDING.value,
        JobStatus.RUNNING.value
    ))

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0


def is_job_cancelled(job_id: str) -> bool:
    """Check if a job has been cancelled."""
    with _cancelled_jobs_lock:
        if job_id in _cancelled_jobs:
            return True
    
    # Double-check in database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT cancelled FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0]:
        with _cancelled_jobs_lock:
            _cancelled_jobs.add(job_id)
        return True
    
    return False


def get_job(job_id: str) -> Optional[dict]:
    """Get job by ID."""
    ensure_jobs_table()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def get_active_jobs() -> list:
    """Get all pending or running jobs."""
    ensure_jobs_table()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        WHERE status IN (?, ?)
        ORDER BY created_at DESC
    """, (JobStatus.PENDING.value, JobStatus.RUNNING.value))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_recent_jobs(limit: int = 10) -> list:
    """Get recent jobs including completed ones."""
    ensure_jobs_table()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM jobs
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def cleanup_old_jobs(hours: int = 24):
    """Remove completed/failed jobs older than specified hours."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM jobs
        WHERE status IN (?, ?)
        AND completed_at < datetime('now', ?)
    """, (JobStatus.COMPLETED.value, JobStatus.FAILED.value, f'-{hours} hours'))

    conn.commit()
    conn.close()


def cleanup_orphaned_jobs():
    """Resume or cleanup interrupted jobs from previous session."""
    ensure_jobs_table()

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find all jobs that were running when server stopped
    cursor.execute("""
        SELECT id, type FROM jobs
        WHERE status IN (?, ?)
        ORDER BY created_at
    """, (JobStatus.PENDING.value, JobStatus.RUNNING.value))

    orphaned_jobs = cursor.fetchall()
    conn.close()

    if not orphaned_jobs:
        return

    resumable_types = {JobType.NEWS_SYNC.value, JobType.STATUS_SYNC.value}
    resumed = 0
    failed = 0

    for job_row in orphaned_jobs:
        job_id = job_row['id']
        job_type = job_row['type']

        # Resume NEWS_SYNC and STATUS_SYNC jobs automatically
        if job_type in resumable_types:
            # Reset to PENDING and update message
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE jobs
                SET status = ?, message = ?, updated_at = ?
                WHERE id = ?
            """, (
                JobStatus.PENDING.value,
                "Resuming after restart (cache will skip completed items)...",
                datetime.now().isoformat(),
                job_id
            ))
            conn.commit()
            conn.close()

            # Relaunch the job with force=False (respects cache)
            try:
                if job_type == JobType.NEWS_SYNC.value:
                    from ..services.news_sync import sync_news_job
                    run_job_async(job_id, lambda jid: sync_news_job(jid, force=False, max_items=10))
                    print(f"[JOBS] Resumed NEWS_SYNC job {job_id}")
                    resumed += 1
                elif job_type == JobType.STATUS_SYNC.value:
                    from ..services.status_sync import sync_all_statuses_job
                    run_job_async(job_id, lambda jid: sync_all_statuses_job(jid, store='steam', force=False))
                    print(f"[JOBS] Resumed STATUS_SYNC job {job_id}")
                    resumed += 1
            except Exception as e:
                print(f"[JOBS] Failed to resume job {job_id}: {e}")
                fail_job(job_id, f"Resume failed: {e}")
                failed += 1
        else:
            # Other job types: mark as failed (too complex to resume)
            update_job = sqlite3.connect(DATABASE_PATH)
            cursor = update_job.cursor()
            cursor.execute("""
                UPDATE jobs
                SET status = ?, error = ?, completed_at = ?, updated_at = ?
                WHERE id = ?
            """, (
                JobStatus.FAILED.value,
                "Server restarted - job type cannot auto-resume",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                job_id
            ))
            update_job.commit()
            update_job.close()
            failed += 1

    if resumed > 0:
        print(f"[JOBS] Auto-resumed {resumed} interrupted job(s)")
    if failed > 0:
        print(f"[JOBS] Marked {failed} non-resumable job(s) as failed")


# Thread-safe job runner
_job_threads: dict[str, threading.Thread] = {}


def run_job_async(job_id: str, job_func: Callable[[str], None]):
    """Run a job function in a background thread."""
    def wrapper():
        try:
            job_func(job_id)
        except Exception as e:
            fail_job(job_id, str(e))
        finally:
            # Cleanup thread reference
            if job_id in _job_threads:
                del _job_threads[job_id]

    thread = threading.Thread(target=wrapper, daemon=True)
    _job_threads[job_id] = thread
    thread.start()

    return job_id
