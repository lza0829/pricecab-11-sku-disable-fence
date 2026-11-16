from __future__ import annotations

from typing import Any

from app.db import connect
from app.repositories import sales as sales_repo
from app.repositories import prices as price_repo


def reconcile_sales() -> dict[str, Any]:
    """Compare each sale's unit_price with the price book value effective at sold_at.

    Sales whose SKU is currently disabled form their own bucket
    (``disabled_sku``): they are never silently counted as a match, even when
    the price happens to agree, because the catalog no longer treats that SKU
    as sellable and the comparison is not meaningful.
    """
    conn = connect()
    try:
        sales = sales_repo.list_sales_with_sku_state(conn)
        rows = []
        match = 0
        mismatch = 0
        missing = 0
        disabled = 0
        for s in sales:
            expected = price_repo.price_at(conn, s["sku_code"], s["sold_at"])
            sold = float(s["unit_price"])
            delta = None if expected is None else round(sold - expected, 4)
            sku_enabled = s.get("sku_enabled")
            if sku_enabled is not None and not bool(sku_enabled):
                # 停用商品成交行：单独分桶，不参与一致/不一致计数。
                status = "disabled_sku"
                disabled += 1
            elif expected is None:
                status = "missing_price"
                missing += 1
            elif abs(expected - sold) < 1e-9:
                status = "match"
                match += 1
                delta = 0.0
            else:
                status = "mismatch"
                mismatch += 1
            rows.append(
                {
                    **s,
                    "sku_enabled": None if sku_enabled is None else bool(sku_enabled),
                    "expected_price": expected,
                    "delta": delta,
                    "status": status,
                }
            )
        return {
            "sale_count": len(sales),
            "match_count": match,
            "mismatch_count": mismatch,
            "missing_count": missing,
            "disabled_sku_count": disabled,
            "compared_count": len(sales) - disabled,
            "rows": rows,
        }
    finally:
        conn.close()


def list_price_book() -> list[dict[str, Any]]:
    conn = connect()
    try:
        return price_repo.list_book(conn)
    finally:
        conn.close()


def list_history(sku_code: str | None = None) -> list[dict[str, Any]]:
    conn = connect()
    try:
        return price_repo.list_history(conn, sku_code=sku_code)
    finally:
        conn.close()
