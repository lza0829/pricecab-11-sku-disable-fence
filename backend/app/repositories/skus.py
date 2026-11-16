from __future__ import annotations

import sqlite3
from typing import Any


def list_skus(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        '''
        SELECT s.id, s.sku_code, s.title, s.category, s.list_price, s.enabled,
               b.current_price, b.source_ticket_no, b.effective_at AS price_effective_at
        FROM skus s
        LEFT JOIN price_book b ON b.sku_code = s.sku_code
        ORDER BY s.sku_code
        '''
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_code(conn: sqlite3.Connection, sku_code: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM skus WHERE sku_code=?", (sku_code,)).fetchone()
    return dict(row) if row else None


def set_enabled(conn: sqlite3.Connection, sku_code: str, enabled: bool) -> None:
    conn.execute(
        "UPDATE skus SET enabled=? WHERE sku_code=?",
        (1 if enabled else 0, sku_code),
    )


def enabled_map(conn: sqlite3.Connection, sku_codes: list[str]) -> dict[str, bool]:
    """Return {sku_code: enabled} for the given codes (missing codes are omitted)."""
    unique = sorted({code for code in sku_codes})
    if not unique:
        return {}
    placeholders = ",".join("?" for _ in unique)
    rows = conn.execute(
        f"SELECT sku_code, enabled FROM skus WHERE sku_code IN ({placeholders})",
        unique,
    ).fetchall()
    return {r["sku_code"]: bool(r["enabled"]) for r in rows}
