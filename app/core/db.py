"""
Lightweight SQLite store for post history + engagement metrics, used by the
dashboard's "Posting History" tab.
"""
import sqlite3
import os
import time
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "posts.db")


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_id TEXT,
                caption TEXT,
                trends TEXT,
                image_path TEXT,
                created_at REAL,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                reach INTEGER DEFAULT 0,
                status TEXT DEFAULT 'posted'
            )
            """
        )


def add_post(media_id: str, caption: str, trends: str, image_path: str, status: str = "posted"):
    init_db()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO posts (media_id, caption, trends, image_path, created_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (media_id, caption, trends, image_path, time.time(), status),
        )


def update_metrics(media_id: str, likes: int, comments: int, reach: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE posts SET likes = ?, comments = ?, reach = ? WHERE media_id = ?",
            (likes, comments, reach, media_id),
        )


def fetch_all_posts():
    init_db()
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
