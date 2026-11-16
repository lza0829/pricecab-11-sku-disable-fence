from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.concurrency import apply_gate
from app.db import connect
from app.policies import POLICY_REJECT, POLICY_SKIP, get_policy
from app.repositories import settings as settings_repo
from app.repositories import tickets as ticket_repo
from app.repositories import prices as price_repo
from app.repositories import skus as sku_repo
from app.repositories import batches as batch_repo


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_clock() -> dict[str, Any]:
    conn = connect()
    try:
        return {
            "business_clock": settings_repo.get(conn, "business_clock"),
            "clock_label": settings_repo.get(conn, "clock_label"),
        }
    finally:
        conn.close()


def set_clock(clock_at: str) -> dict[str, Any]:
    clock_at = (clock_at or "").strip()
    if not clock_at:
        raise HTTPException(400, "业务钟不能为空")
    conn = connect(immediate=True)
    try:
        settings_repo.set_value(conn, "business_clock", clock_at)
        conn.commit()
        return get_clock()
    finally:
        conn.close()


def list_batches() -> list[dict[str, Any]]:
    conn = connect()
    try:
        return batch_repo.list_batches(conn)
    finally:
        conn.close()


def _disabled_skus(conn, lines: list[dict[str, Any]]) -> list[str]:
    state = sku_repo.enabled_map(conn, [line["sku_code"] for line in lines])
    return sorted(
        {
            line["sku_code"]
            for line in lines
            if state.get(line["sku_code"], False) is not True
        }
    )


def apply_due() -> dict[str, Any]:
    """Apply all scheduled tickets whose effective_at <= business clock.

    The whole cycle runs under ``apply_gate`` and one BEGIN IMMEDIATE
    transaction, so:

    * enable/disable switches cannot interleave with it (they are rejected
      while it runs), and
    * either the whole batch is written or nothing is (rollback on error).

    Disabled SKUs are governed by the single global policy:
    ``reject_on_create`` rejects the whole ticket (no line of it touches the
    price book); ``skip_on_apply`` skips disabled lines, counts them, and still
    writes enabled lines.
    """
    if not apply_gate.acquire(blocking=False):
        raise HTTPException(409, "已有应用进行中，请等待其结束")
    try:
        conn = connect(immediate=True)
        try:
            clock = settings_repo.get(conn, "business_clock")
            if not clock:
                raise HTTPException(400, "业务钟未设置")
            due = ticket_repo.due_tickets(conn, clock)
            if not due:
                conn.commit()
                return {
                    "applied": False,
                    "message": "当前业务钟下没有到期改价单",
                    "business_clock": clock,
                    "ticket_count": 0,
                    "line_count": 0,
                    "skipped_line_count": 0,
                    "rejected_ticket_count": 0,
                    "rejected_tickets": [],
                    "skipped_lines": [],
                }

            policy = get_policy(conn)
            batch_no = batch_repo.next_batch_no(conn)
            created = _now()
            line_total = 0
            skipped_line_total = 0
            applied_tickets: list[str] = []
            rejected_tickets: list[dict[str, Any]] = []
            skipped_lines: list[dict[str, Any]] = []
            batch_id = batch_repo.create_batch(
                conn,
                batch_no=batch_no,
                clock_at=clock,
                ticket_count=0,
                line_count=0,
                status="running",
                created_at=created,
            )

            for t in due:
                lines = ticket_repo.list_lines(conn, t["id"])
                disabled = _disabled_skus(conn, lines)

                if disabled and policy == POLICY_REJECT:
                    # 整单拒绝：不写任何一行，价签本不被该单改写。状态不再
                    # 是 scheduled，重新启用该商品也不会让本单日后偷偷生效。
                    reason = "含停用商品：" + "、".join(disabled)
                    ticket_repo.mark_rejected(
                        conn,
                        t["id"],
                        rejected_at=created,
                        batch_id=batch_id,
                        reason=reason,
                    )
                    rejected_tickets.append(
                        {
                            "ticket_no": t["ticket_no"],
                            "reason": reason,
                            "disabled_skus": disabled,
                        }
                    )
                    continue

                for line in lines:
                    if policy == POLICY_SKIP and line["sku_code"] in disabled:
                        skipped_line_total += 1
                        skipped_lines.append(
                            {
                                "ticket_no": t["ticket_no"],
                                "sku_code": line["sku_code"],
                                "new_price": float(line["new_price"]),
                            }
                        )
                        continue
                    price_repo.upsert_book(
                        conn,
                        sku_code=line["sku_code"],
                        price=float(line["new_price"]),
                        ticket_no=t["ticket_no"],
                        effective_at=t["effective_at"],
                        updated_at=created,
                    )
                    line_total += 1
                ticket_repo.mark_applied(conn, t["id"], applied_at=created, batch_id=batch_id)
                applied_tickets.append(t["ticket_no"])

            batch_repo.finish_batch(
                conn,
                batch_id=batch_id,
                ticket_count=len(applied_tickets),
                line_count=line_total,
                rejected_ticket_count=len(rejected_tickets),
                skipped_line_count=skipped_line_total,
                status="done",
            )
            conn.commit()
            return {
                "applied": bool(applied_tickets),
                "batch_no": batch_no,
                "business_clock": clock,
                "disabled_sku_policy": policy,
                "ticket_count": len(applied_tickets),
                "line_count": line_total,
                "skipped_line_count": skipped_line_total,
                "rejected_ticket_count": len(rejected_tickets),
                "tickets": applied_tickets,
                "rejected_tickets": rejected_tickets,
                "skipped_lines": skipped_lines,
            }
        except HTTPException:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    finally:
        apply_gate.release()
