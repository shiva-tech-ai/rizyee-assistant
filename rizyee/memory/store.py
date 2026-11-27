"""
RIZYEE Memory Store
===================
Stores facts and reminders in a local SQLite database.

This is Milestone 4 — RIZYEE can now REMEMBER things you tell it
and REMIND you at a time you set.

Two kinds of memory:
    1. Facts: "remember that my wifi password is mango123"
       Later you can ask "what is my wifi password" and RIZYEE recalls it.
    2. Reminders: "remind me to drink water at 4 pm"
       RIZYEE speaks the reminder out loud when the time comes.

Why SQLite:
    It's built into Python (the `sqlite3` module), so there's nothing
    to install — perfect for a ₹0 budget project. The whole database
    is one file on disk (data/rizyee.db), which is easy to back up
    or delete.

Database tables:
    facts       (id, key, value, created_at)
    reminders    (id, what, when_iso, done)

Usage:
    from rizyee.memory.store import MemoryStore
    store = MemoryStore()
    store.save_fact("wifi password", "mango123")
    store.get_fact("wifi password")  # → "mango123"
    store.add_reminder("drink water", "2026-11-04T16:00:00")
    store.due_reminders()             # → list of reminders whose time has come
"""

import os
import sqlite3
from datetime import datetime

from rizyee.utils.logger import get_logger

logger = get_logger("memory.store")

# ── Where the database file lives ──
# This file is at: rizyee/memory/store.py  →  project root is ../../
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "rizyee.db")


class MemoryStore:
    """
    A thin wrapper around a SQLite database for facts and reminders.

    Why a class (not just functions):
        We open one connection and reuse it. Opening a new connection
        for every call would be slow and could hit file-lock issues.
        The class also gives one clean place to create the tables
        the first time RIZYEE runs.
    """

    def __init__(self, db_path: str = DB_PATH):
        """
        Open (or create) the database and make sure the tables exist.

        Args:
            db_path: Path to the .db file. Defaults to data/rizyee.db.
        """
        # Make sure the data/ folder exists before we try to write in it.
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # check_same_thread=False lets the reminder checker (which runs
        # in a background thread) use the same connection safely for reads.
        # We only write from the main thread, so there's no race.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        # Return rows as dicts (column name → value) instead of tuples,
        # so code reads as store.get_fact(...) instead of row[2].
        self.conn.row_factory = sqlite3.Row

        self._create_tables()
        logger.info("Memory store ready.")

    def _create_tables(self) -> None:
        """Create the facts and reminders tables if they don't exist yet."""
        # "IF NOT EXISTS" means this is safe to run every time — it only
        # actually creates the table the first time.
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                key        TEXT NOT NULL UNIQUE,
                value      TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                what     TEXT NOT NULL,
                when_iso TEXT NOT NULL,
                done      INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self.conn.commit()

    # ── FACTS ──────────────────────────────────────────────

    def save_fact(self, key: str, value: str) -> None:
        """
        Remember a fact. If the key already exists, update its value.

        Args:
            key:   What the fact is about, e.g. "wifi password".
            value: The fact itself, e.g. "mango123".
        """
        now = datetime.now().isoformat(timespec="seconds")
        # "INSERT ... ON CONFLICT DO UPDATE" is SQLite's upsert:
        # it inserts a new row, OR if the key already exists, it updates
        # the value and timestamp instead of failing.
        self.conn.execute(
            """
            INSERT INTO facts (key, value, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                created_at = excluded.created_at
            """,
            (key.lower(), value, now),
        )
        self.conn.commit()
        logger.info(f"Saved fact: '{key}' = '{value}'")

    def get_fact(self, key: str):
        """
        Recall a fact by key.

        Args:
            key: The fact's label, e.g. "wifi password".

        Returns:
            The stored value as a string, or None if RIZYEE doesn't know it.
        """
        row = self.conn.execute(
            "SELECT value FROM facts WHERE key = ?", (key.lower(),)
        ).fetchone()
        if row is None:
            logger.info(f"No fact found for: '{key}'")
            return None
        logger.info(f"Recalled fact: '{key}' = '{row['value']}'")
        return row["value"]

    def list_facts(self) -> list:
        """
        Return all known facts as a list of (key, value) tuples.
        Useful for "what do you remember" type questions.
        """
        rows = self.conn.execute(
            "SELECT key, value FROM facts ORDER BY key"
        ).fetchall()
        return [(r["key"], r["value"]) for r in rows]

    def forget_fact(self, key: str) -> bool:
        """
        Delete a fact.

        Returns:
            True if a fact was deleted, False if the key wasn't known.
        """
        cur = self.conn.execute(
            "DELETE FROM facts WHERE key = ?", (key.lower(),)
        )
        self.conn.commit()
        deleted = cur.rowcount > 0
        logger.info(f"Forget fact '{key}': deleted={deleted}")
        return deleted

    # ── REMINDERS ──────────────────────────────────────────

    def add_reminder(self, what: str, when_iso: str) -> None:
        """
        Schedule a reminder.

        Args:
            what:     The message to speak when the reminder fires.
            when_iso: When to fire it, in ISO format
                      (e.g. "2026-11-04T16:00:00").
        """
        self.conn.execute(
            "INSERT INTO reminders (what, when_iso) VALUES (?, ?)",
            (what, when_iso),
        )
        self.conn.commit()
        logger.info(f"Reminder set: '{what}' at {when_iso}")

    def due_reminders(self) -> list:
        """
        Return reminders whose time has come and haven't fired yet.

        Returns:
            A list of dicts: [{"id": int, "what": str, "when_iso": str}, ...]
        """
        now = datetime.now().isoformat(timespec="seconds")
        rows = self.conn.execute(
            """
            SELECT id, what, when_iso FROM reminders
            WHERE done = 0 AND when_iso <= ?
            ORDER BY when_iso
            """,
            (now,),
        ).fetchall()
        return [{"id": r["id"], "what": r["what"], "when_iso": r["when_iso"]}
                for r in rows]

    def mark_reminder_done(self, reminder_id: int) -> None:
        """Mark a reminder as fired so it doesn't fire again."""
        self.conn.execute(
            "UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,)
        )
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection. Call this when RIZYEE shuts down."""
        self.conn.close()
        logger.info("Memory store closed.")
