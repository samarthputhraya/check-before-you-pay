"""SQLite access. One file in WAL mode, on the Railway volume in production (SQLITE_PATH=/data/app.db).

The skeleton only opens and pings the database. Role B adds the link tables from BUILD_BRIEF section 7 here.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=2.0)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=2000")
    return con


def ping(path: Path) -> bool:
    try:
        con = connect(path)
        try:
            # a write lock, not just a read: a read-only volume must report "down"
            con.execute("BEGIN IMMEDIATE")
            con.execute("ROLLBACK")
        finally:
            con.close()
        return True
    except (sqlite3.Error, OSError):
        return False
