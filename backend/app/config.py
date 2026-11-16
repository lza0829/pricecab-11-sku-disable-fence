from __future__ import annotations

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", str(Path(__file__).resolve().parents[2] / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "pricecab.db"
PROJECT = "pricecab"
PROJECT_NAME = "价签柜"

# 停用商品的改价/应用策略。两种策略互斥，全局只贯彻一种，由部署时选定：
#   reject_on_create  ——「建单即拒」：停用商品不得进入新改价明细；
#                        已存在的 scheduled 单若含停用商品，应用时整单拒绝，
#                        价签本不得被该单改写。
#   skip_on_apply     ——「允许建单但应用跳过」：scheduled 单可含停用商品；
#                        应用时跳过停用行并计数，不写其价签，启用行照常写入；
#                        重新启用后须新的应用周期或新单才写入该商品。
# 默认 reject_on_create。可用环境变量 DISABLED_SKU_POLICY 选择另一种；无论选
# 哪种，建单与应用都读同一个全局值，绝不各按一套。
DISABLED_SKU_POLICY = os.environ.get("DISABLED_SKU_POLICY", "reject_on_create")
if DISABLED_SKU_POLICY not in {"reject_on_create", "skip_on_apply"}:
    raise ValueError(f"未知 DISABLED_SKU_POLICY：{DISABLED_SKU_POLICY}")
