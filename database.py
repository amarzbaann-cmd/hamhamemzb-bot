import sqlite3
import os
from datetime import datetime
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
DB_PATH = os.environ.get("DB_PATH", "defects.db")


class Database:
    def __init__(self):
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS defects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    size TEXT NOT NULL,
                    color TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_code ON defects(code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON defects(created_at)")
            conn.commit()
        logger.info("Database initialized.")

    def add_defect(self, code, size, color, quantity, created_at):
        created_str = created_at.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO defects (code,size,color,quantity,created_at) VALUES (?,?,?,?,?)",
                (code, size, color, quantity, created_str)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_defects(self) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM defects ORDER BY code, size, color"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_defects_by_code(self, code: str) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM defects WHERE code=? ORDER BY created_at DESC",
                (code,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_defects_since(self, since: datetime) -> List[Dict]:
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM defects WHERE created_at >= ? ORDER BY code,size,color",
                (since_str,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_defects_by_date(self, date_str: str) -> List[Dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM defects WHERE created_at LIKE ? ORDER BY code",
                (f"{date_str}%",)
            ).fetchall()
        return [dict(r) for r in rows]
