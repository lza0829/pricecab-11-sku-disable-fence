from __future__ import annotations

import sqlite3
from typing import Any


def next_batch_no(conn: sqlite3.Connection) -> str:
    n = conn.execute("SELECT COUNT(*) c FROM apply_batches").fetchone()["c"] + 1
    return f"AB-{n:04d}"


def create_batch(
    conn: sqlite3.Connection,
    *,
    batch_no: str,
    clock_at: str,
    ticket_count: int,
    line_count: int,
    status: str,
    created_at: str,
    rejected_ticket_count: int = 0,
    skipped_line_count: int = 0,
) -> int:
    cur = conn.execute(
        '''
        INSERT INTO apply_batches(
          batch_no, clock_at, ticket_count, line_count, status, created_at,
          rejected_ticket_count, skipped_line_count
        )
        VALUES (?,?,?,?,?,?,?,?)
        ''',
        (
            batch_no,
            clock_at,
            ticket_count,
            line_count,
            status,
            created_at,
            rejected_ticket_count,
            skipped_line_count,
        ),
    )
    return int(cur.lastrowid)


def finish_batch(
    conn: sqlite3.Connection,
    *,
    batch_id: int,
    ticket_count: int,
    line_count: int,
    rejected_ticket_count: int,
    skipped_line_count: int = 0,
    status: str = "done",
) -> None:
    conn.execute(
        '''
        UPDATE apply_batches
        SET ticket_count=?, line_count=?, rejected_ticket_count=?,
            skipped_line_count=?, status=?
        WHERE id=?
        ''',
        (
            ticket_count,
            line_count,
            rejected_ticket_count,
            skipped_line_count,
            status,
            batch_id,
        ),
    )


def list_batches(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM apply_batches ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
