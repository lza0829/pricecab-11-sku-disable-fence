from __future__ import annotations

import sqlite3
from typing import Any

from app.config import DB_PATH


def connect(*, immediate: bool = False) -> sqlite3.Connection:
    # timeout: concurrent writers (apply vs. enable/disable) wait for the
    # transaction lock instead of failing with "database is locked".
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if immediate:
        conn.execute("BEGIN IMMEDIATE")
    return conn


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None
