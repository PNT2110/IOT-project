from __future__ import annotations

from fastapi import APIRouter

from .routers import accounts, auth, device, flights, misc, zones


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    for module in (misc, auth, zones, accounts, flights, device):
        router.include_router(module.router)
    return router
