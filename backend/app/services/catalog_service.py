from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.concurrency import apply_gate, sku_write_gate
from app.db import connect
from app.policies import describe_current
from app.repositories import skus as sku_repo
from app.repositories import settings as settings_repo
from app.repositories import tickets as ticket_repo
from app.repositories import prices as price_repo
from app.repositories import sales as sales_repo


def dashboard() -> dict[str, Any]:
    conn = connect()
    try:
        clock = settings_repo.get(conn, "business_clock")
        return {
            "project": "pricecab",
            "name": "价签柜",
            "business_clock": clock,
            "sku_count": conn.execute("SELECT COUNT(*) c FROM skus").fetchone()["c"],
            "enabled_sku_count": conn.execute(
                "SELECT COUNT(*) c FROM skus WHERE enabled=1"
            ).fetchone()["c"],
            "disabled_sku_count": conn.execute(
                "SELECT COUNT(*) c FROM skus WHERE enabled=0"
            ).fetchone()["c"],
            "ticket_count": conn.execute("SELECT COUNT(*) c FROM price_tickets").fetchone()["c"],
            "scheduled_count": conn.execute(
                "SELECT COUNT(*) c FROM price_tickets WHERE status='scheduled'"
            ).fetchone()["c"],
            "applied_count": conn.execute(
                "SELECT COUNT(*) c FROM price_tickets WHERE status='applied'"
            ).fetchone()["c"],
            "rejected_count": conn.execute(
                "SELECT COUNT(*) c FROM price_tickets WHERE status='rejected'"
            ).fetchone()["c"],
            "book_count": conn.execute("SELECT COUNT(*) c FROM price_book").fetchone()["c"],
            "sale_count": conn.execute("SELECT COUNT(*) c FROM sales_fixture").fetchone()["c"],
            "batch_count": conn.execute("SELECT COUNT(*) c FROM apply_batches").fetchone()["c"],
            "due_now": len(ticket_repo.due_tickets(conn, clock or "")),
            **describe_current(conn),
        }
    finally:
        conn.close()


def list_skus() -> list[dict[str, Any]]:
    conn = connect()
    try:
        return sku_repo.list_skus(conn)
    finally:
        conn.close()


def get_sku(sku_code: str) -> dict[str, Any]:
    conn = connect()
    try:
        sku = sku_repo.get_by_code(conn, sku_code)
        if not sku:
            raise HTTPException(404, f"商品不存在 {sku_code}")
        sku["enabled"] = bool(sku["enabled"])
        sku["scheduled_tickets"] = ticket_repo.scheduled_ticket_nos_with_sku(conn, sku_code)
        return sku
    finally:
        conn.close()


def set_sku_enabled(sku_code: str, enabled: bool) -> dict[str, Any]:
    """Enable / disable a SKU.

    Rejected outright while an apply cycle is running so that no apply can ever
    observe a half-switched catalog. Otherwise the switch is a single DB
    transaction serialised against apply and ticket creation via BEGIN IMMEDIATE.
    """
    if not apply_gate.acquire(blocking=False):
        raise HTTPException(409, "应用进行中，不能切换商品启停；请等待本应用结束后重试")
    try:
        with sku_write_gate:
            conn = connect(immediate=True)
            try:
                sku = sku_repo.get_by_code(conn, sku_code)
                if not sku:
                    raise HTTPException(404, f"商品不存在 {sku_code}")
                was_enabled = bool(sku["enabled"])
                if was_enabled != enabled:
                    sku_repo.set_enabled(conn, sku_code, enabled)
                conn.commit()
            except HTTPException:
                conn.rollback()
                raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return get_sku(sku_code)
    finally:
        apply_gate.release()
