"""
Job storage database layer using SQLite
"""
import sqlite3
import threading
import json
from contextlib import contextmanager
from typing import Optional, Dict, Any


class JobStorage:
    """Persistent job storage using SQLite"""
    
    def __init__(self, db_path: str = "jobs.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database operations"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
    
    def _init_db(self):
        """Initialize the database schema"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    result TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index for efficient lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_jobs_status 
                ON jobs(status, created_at)
            """)
    
    def create_job(self, job_data: Dict[str, Any]) -> None:
        """Create a new job"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO jobs (job_id, status, progress, result, error)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_data["job_id"],
                job_data["status"],
                job_data["progress"],
                json.dumps(job_data.get("result")) if job_data.get("result") else None,
                job_data.get("error")
            ))
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                SELECT job_id, status, progress, result, error
                FROM jobs WHERE job_id = ?
            """, (job_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "job_id": row['job_id'],
                    "status": row['status'],
                    "progress": row['progress'],
                    "result": json.loads(row['result']) if row['result'] else None,
                    "error": row['error']
                }
            return None
    
    def update_job(self, job_data: Dict[str, Any]) -> None:
        """Update an existing job"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                UPDATE jobs 
                SET status = ?, progress = ?, result = ?, error = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (
                job_data["status"],
                job_data["progress"],
                json.dumps(job_data.get("result")) if job_data.get("result") else None,
                job_data.get("error"),
                job_data["job_id"]
            ))
    
    def cleanup_old_jobs(self, days: int = 7) -> int:
        """Clean up jobs older than specified days"""
        with self._get_cursor() as cursor:
            cursor.execute("""
                DELETE FROM jobs 
                WHERE created_at < datetime('now', '-{} days')
            """.format(days))
            return cursor.rowcount