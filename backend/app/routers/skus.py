from fastapi import APIRouter
from pydantic import BaseModel

from app.services import catalog_service as catalog

router = APIRouter(prefix="/skus", tags=["skus"])


class SkuEnabledIn(BaseModel):
    enabled: bool


@router.get("")
def list_skus():
    return catalog.list_skus()


@router.get("/{sku_code}")
def get_sku(sku_code: str):
    return catalog.get_sku(sku_code)


@router.put("/{sku_code}/enabled")
def set_sku_enabled(sku_code: str, body: SkuEnabledIn):
    return catalog.set_sku_enabled(sku_code, body.enabled)
