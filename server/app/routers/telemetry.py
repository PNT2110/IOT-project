"""Telemetry streaming and live query endpoints."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .deps import _db, _now_iso, _session, ok

router = APIRouter(tags=["telemetry"])


@router.get("/telemetry/latest")
def get_latest_telemetry(
    request: Request,
    db: Session = Depends(_db),
    device_id: str | None = None,
):
    """Retrieve the latest ingested telemetry sample."""
    _session(request, db)
    cache = getattr(request.app.state, "latest_telemetry", {})
    if device_id:
        telem = cache.get(device_id)
    else:
        telem = cache.get("__latest__")

    if telem is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "TELEMETRY_NOT_FOUND", "message_for_user": "No telemetry found"},
        )
    return ok({"telemetry": telem}, request.state.request_id, _now_iso())


@router.get("/telemetry/stream")
async def stream_telemetry(
    request: Request,
    device_id: str | None = None,
    limit: int | None = None,
):
    """Live push telemetry stream via Server-Sent Events (SSE)."""
    async def event_generator():
        count = 0
        last_seq = None
        while True:
            if await request.is_disconnected():
                break
            if limit is not None and count >= limit:
                break
            cache = getattr(request.app.state, "latest_telemetry", {})
            telem = cache.get(device_id) if device_id else cache.get("__latest__")
            if telem and telem.get("seq") != last_seq:
                last_seq = telem.get("seq")
                data_str = json.dumps(telem)
                count += 1
                yield f"data: {data_str}\n\n"
            if limit is not None and count >= limit:
                break
            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

