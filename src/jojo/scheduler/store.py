"""
Job 持久化 — SQLite 存储，重启不丢失。
"""

import sqlite3
import time
from pathlib import Path

from src.jojo.scheduler.models import CronJob
from src.jojo.config import config
from src.jojo.logger import logger


class JobStore:
    """Cron Job 的 SQLite 持久化存储。"""

    def __init__(self):
        db_path = Path(config.scheduler.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                cron TEXT NOT NULL,
                task TEXT NOT NULL,
                agent TEXT DEFAULT 'researcher',
                enabled INTEGER DEFAULT 1,
                created_at REAL NOT NULL,
                last_run_at REAL,
                run_count INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    # ========== 增删查 ==========

    def save(self, job: CronJob) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO jobs VALUES
               (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (job.id, job.name, job.cron, job.task, job.agent,
             1 if job.enabled else 0, job.created_at,
             job.last_run_at, job.run_count),
        )
        self._conn.commit()

    def get(self, job_id: str) -> CronJob | None:
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return self._row_to_job(row) if row else None

    def list_all(self) -> list[CronJob]:
        rows = self._conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_job(r) for r in rows if r]

    def delete(self, job_id: str) -> bool:
        cur = self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def mark_run(self, job_id: str) -> None:
        now = time.time()
        self._conn.execute(
            "UPDATE jobs SET last_run_at = ?, run_count = run_count + 1 WHERE id = ?",
            (now, job_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_job(row: tuple) -> CronJob:
        return CronJob(
            id=row[0], name=row[1], cron=row[2], task=row[3],
            agent=row[4] or "researcher",
            enabled=bool(row[5]), created_at=row[6],
            last_run_at=row[7], run_count=row[8] or 0,
        )
