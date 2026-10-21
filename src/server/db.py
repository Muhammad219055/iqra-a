"""
Local SQLite Database Module for Quran Tutor.
Stores session summaries, mistake logs, and memorization peek counts.
Matches the local-first, zero-cloud architecture.
"""

from pathlib import Path
import sqlite3
import time
from typing import Dict, List, Optional
import uuid

DB_PATH = Path("data/user_db.sqlite")


def init_db(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        surah INTEGER NOT NULL,
        start_time INTEGER NOT NULL,
        end_time INTEGER NOT NULL,
        total_words_matched INTEGER DEFAULT 0,
        total_mistakes INTEGER DEFAULT 0,
        total_prompts INTEGER DEFAULT 0,
        total_peeks INTEGER DEFAULT 0,
        accuracy REAL DEFAULT 0.0
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mistakes (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        mistake_type TEXT NOT NULL,
        surah INTEGER NOT NULL,
        ayah INTEGER NOT NULL,
        word INTEGER NOT NULL,
        expected_text TEXT,
        received_text TEXT,
        timestamp INTEGER NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    );
    """)

    conn.commit()
    conn.close()


def save_session(
    surah: int,
    start_time: int,
    end_time: int,
    total_words_matched: int,
    total_mistakes: int,
    total_prompts: int,
    total_peeks: int,
    accuracy: float,
    mistakes_list: List[dict],
    db_path: Path = DB_PATH,
) -> str:
    init_db(db_path)
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO sessions (
        session_id, surah, start_time, end_time,
        total_words_matched, total_mistakes, total_prompts, total_peeks, accuracy
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id, surah, start_time, end_time,
        total_words_matched, total_mistakes, total_prompts, total_peeks, accuracy
    ))

    for m in mistakes_list:
        m_id = str(uuid.uuid4())
        cursor.execute("""
        INSERT INTO mistakes (
            id, session_id, mistake_type, surah, ayah, word,
            expected_text, received_text, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m_id,
            session_id,
            m.get("mistake_type") or m.get("type", "UNKNOWN"),
            m.get("surah", surah),
            m.get("ayah", 1),
            m.get("word", 1),
            m.get("expected_text", ""),
            m.get("received_text", ""),
            m.get("timestamp", int(time.time())),
        ))

    conn.commit()
    conn.close()
    return session_id


def get_recent_sessions(limit: int = 10, db_path: Path = DB_PATH) -> List[dict]:
    init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM sessions ORDER BY start_time DESC LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()

    sessions = []
    for r in rows:
        cursor.execute("""
        SELECT * FROM mistakes WHERE session_id = ? ORDER BY timestamp ASC
        """, (r["session_id"],))
        mistake_rows = cursor.fetchall()

        s_dict = dict(r)
        s_dict["mistakes"] = [dict(m) for m in mistake_rows]
        sessions.append(s_dict)

    conn.close()
    return sessions
