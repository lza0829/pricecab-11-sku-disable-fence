from __future__ import annotations

import sqlite3

from app.config import DISABLED_SKU_POLICY
from app.repositories import settings as settings_repo


# 两种「停用商品如何影响改价/应用」策略。全局只贯彻一种：settings 表里的
# disabled_sku_policy 存哪个，整个应用（建单、应用）就按哪个执行，绝不混用。
POLICY_REJECT = "reject_on_create"
POLICY_SKIP = "skip_on_apply"

POLICIES: dict[str, dict[str, str]] = {
    POLICY_REJECT: {
        "label": "建单即拒",
        "summary": "停用商品不得进入新建改价明细；已有 scheduled 单若含停用商品，应用时整单拒绝，价签本不被该单改写。",
    },
    POLICY_SKIP: {
        "label": "允许建单但应用跳过",
        "summary": "scheduled 单可含停用商品；应用时跳过停用行并计数，不写其价签，启用行照常写入；重新启用后须新的应用周期或新单才写入该商品。",
    },
}

DEFAULT_POLICY = DISABLED_SKU_POLICY


class PolicyError(ValueError):
    pass


def get_policy(conn: sqlite3.Connection) -> str:
    value = settings_repo.get(conn, "disabled_sku_policy", DEFAULT_POLICY)
    return value if value in POLICIES else DEFAULT_POLICY


def set_policy(conn: sqlite3.Connection, policy: str) -> None:
    if policy not in POLICIES:
        raise PolicyError(f"未知停用商品策略：{policy}")
    settings_repo.set_value(conn, "disabled_sku_policy", policy)
    settings_repo.set_value(conn, "disabled_sku_policy_label", POLICIES[policy]["label"])


def describe_current(conn: sqlite3.Connection) -> dict[str, str]:
    policy = get_policy(conn)
    meta = POLICIES[policy]
    return {
        "disabled_sku_policy": policy,
        "disabled_sku_policy_label": meta["label"],
        "disabled_sku_policy_summary": meta["summary"],
    }
