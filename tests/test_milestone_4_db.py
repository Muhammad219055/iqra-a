"""
Automated Test for Milestone 4:
Verifies SQLite persistence for recitation sessions and mistake tracking.
"""

from pathlib import Path
import time
from src.server.db import init_db, save_session, get_recent_sessions

TEST_DB = Path("data/test_user_db.sqlite")


def test_milestone_4_persistence():
    print("\n" + "=" * 60)
    print("Testing Milestone 4: SQLite Database Session & Mistake History")
    print("=" * 60)

    if TEST_DB.exists():
        TEST_DB.unlink()

    init_db(TEST_DB)
    print("[Step 1] Initialized test SQLite database.")

    # Save dummy session
    now = int(time.time())
    mistakes = [
        {
            "mistake_type": "MISSED_WORDS",
            "surah": 1,
            "ayah": 1,
            "word": 3,
            "expected_text": "ٱلرَّحْمَـٰنِ",
            "received_text": None,
            "timestamp": now,
        },
        {
            "mistake_type": "PEEKED_WORDS",
            "surah": 1,
            "ayah": 2,
            "word": 1,
            "expected_text": "ٱلْحَمْدُ",
            "received_text": "[PEEKED]",
            "timestamp": now + 5,
        }
    ]

    session_id = save_session(
        surah=1,
        start_time=now,
        end_time=now + 60,
        total_words_matched=25,
        total_mistakes=1,
        total_prompts=1,
        total_peeks=1,
        accuracy=96.1,
        mistakes_list=mistakes,
        db_path=TEST_DB,
    )
    print(f"[Step 2] Saved session with ID: {session_id}")

    # Fetch recent sessions
    recent = get_recent_sessions(limit=5, db_path=TEST_DB)
    assert len(recent) == 1, f"Expected 1 session, found {len(recent)}"
    s = recent[0]
    print(f"[Step 3] Fetched session from SQLite:")
    print(f"  Surah: {s['surah']}, Matched: {s['total_words_matched']}, Accuracy: {s['accuracy']}%")
    print(f"  Mistakes logged: {len(s['mistakes'])}")

    assert s["total_words_matched"] == 25
    assert s["total_peeks"] == 1
    assert len(s["mistakes"]) == 2
    assert s["mistakes"][0]["mistake_type"] == "MISSED_WORDS"
    assert s["mistakes"][1]["mistake_type"] == "PEEKED_WORDS"

    print("  --> PASS: SQLite database session & mistake logging fully verified.")
    print("=" * 60)

    # Cleanup test DB
    if TEST_DB.exists():
        TEST_DB.unlink()


if __name__ == "__main__":
    test_milestone_4_persistence()
