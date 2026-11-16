from __future__ import annotations

import sqlite3
from typing import Any


def next_ticket_no(conn: sqlite3.Connection) -> str:
    n = conn.execute("SELECT COUNT(*) c FROM price_tickets").fetchone()["c"] + 1
    return f"PT-{n:04d}"


def create_ticket(
    conn: sqlite3.Connection,
    *,
    ticket_no: str,
    title: str,
    effective_at: str,
    note: str | None,
    created_at: str,
) -> int:
    cur = conn.execute(
        '''
        INSERT INTO price_tickets(ticket_no, title, status, effective_at, note, created_at)
        VALUES (?,?,?,?,?,?)
        ''',
        (ticket_no, title, "scheduled", effective_at, note, created_at),
    )
    return int(cur.lastrowid)


def add_line(
    conn: sqlite3.Connection,
    *,
    ticket_id: int,
    sku_code: str,
    old_price: float,
    new_price: float,
) -> int:
    cur = conn.execute(
        '''
        INSERT INTO price_ticket_lines(ticket_id, sku_code, old_price, new_price)
        VALUES (?,?,?,?)
        ''',
        (ticket_id, sku_code, old_price, new_price),
    )
    return int(cur.lastrowid)


def list_tickets(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        '''
        SELECT t.*,
               (SELECT COUNT(*) FROM price_ticket_lines l WHERE l.ticket_id=t.id) AS line_count
        FROM price_tickets t
        ORDER BY t.id DESC
        LIMIT ?
        ''',
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_ticket(conn: sqlite3.Connection, ticket_id: int) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM price_tickets WHERE id=?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def list_lines(conn: sqlite3.Connection, ticket_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        '''
        SELECT l.*, s.enabled AS sku_enabled
        FROM price_ticket_lines l
        LEFT JOIN skus s ON s.sku_code = l.sku_code
        WHERE l.ticket_id=?
        ORDER BY l.id
        ''',
        (ticket_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def due_tickets(conn: sqlite3.Connection, clock_at: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        '''
        SELECT * FROM price_tickets
        WHERE status='scheduled' AND effective_at <= ?
        ORDER BY effective_at, id
        ''',
        (clock_at,),
    ).fetchall()
    return [dict(r) for r in rows]


def scheduled_ticket_nos_with_sku(conn: sqlite3.Connection, sku_code: str) -> list[str]:
    rows = conn.execute(
        '''
        SELECT DISTINCT t.ticket_no
        FROM price_tickets t
        JOIN price_ticket_lines l ON l.ticket_id = t.id
        WHERE t.status='scheduled' AND l.sku_code=?
        ORDER BY t.ticket_no
        ''',
        (sku_code,),
    ).fetchall()
    return [r["ticket_no"] for r in rows]


def mark_applied(
    conn: sqlite3.Connection,
    ticket_id: int,
    *,
    applied_at: str,
    batch_id: int,
) -> None:
    conn.execute(
        '''
        UPDATE price_tickets
        SET status='applied', applied_at=?, apply_batch_id=?
        WHERE id=?
        ''',
        (applied_at, batch_id, ticket_id),
    )


def mark_rejected(
    conn: sqlite3.Connection,
    ticket_id: int,
    *,
    rejected_at: str,
    batch_id: int,
    reason: str,
) -> None:
    """Reject a whole ticket; status leaves ``scheduled`` so it is never retried."""
    conn.execute(
        '''
        UPDATE price_tickets
        SET status='rejected', rejected_at=?, reject_reason=?, apply_batch_id=?
        WHERE id=?
        ''',
        (rejected_at, reason, batch_id, ticket_id),
    )
