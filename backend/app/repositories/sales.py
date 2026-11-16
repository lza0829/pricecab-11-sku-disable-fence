from __future__ import annotations

import sqlite3
from typing import Any


def list_sales(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM sales_fixture ORDER BY sold_at, id"
    ).fetchall()
    return [dict(r) for r in rows]


def list_sales_with_sku_state(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Sales joined with the current enable/disable state of their SKU.

    ``sku_enabled`` is NULL when the SKU no longer exists in the catalog.
    """
    rows = conn.execute(
        '''
        SELECT sf.*, s.enabled AS sku_enabled
        FROM sales_fixture sf
        LEFT JOIN skus s ON s.sku_code = sf.sku_code
        ORDER BY sf.sold_at, sf.id
        '''
    ).fetchall()
    return [dict(r) for r in rows]
