import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decode_bridge_token
from app.db.session import SessionLocal
from app.models.league import LeagueMembership
from app.services.realtime import manager

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/leagues/{league_id}")
async def league_realtime(websocket: WebSocket, league_id: uuid.UUID, token: str) -> None:
    """Push channel for live ranking updates and notifications. Browsers
    can't set custom headers on a WebSocket handshake, so the bridge token
    travels as a query param instead of an Authorization header."""
    db = SessionLocal()
    try:
        payload = decode_bridge_token(token)
    except Exception:  # noqa: BLE001
        await websocket.close(code=4401)
        db.close()
        return

    from app.models.user import User

    user = (
        db.query(User)
        .filter(User.auth_provider == payload.provider, User.auth_provider_id == payload.sub)
        .first()
    )
    if user is None:
        await websocket.close(code=4401)
        db.close()
        return

    membership = (
        db.query(LeagueMembership)
        .filter(LeagueMembership.league_id == league_id, LeagueMembership.user_id == user.id, LeagueMembership.is_active.is_(True))
        .first()
    )
    db.close()
    if membership is None:
        await websocket.close(code=4403)
        return

    await manager.connect(league_id, websocket)
    try:
        while True:
            # No inbound protocol yet — the client only listens. Keep the
            # loop alive so `receive` surfaces the disconnect promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(league_id, websocket)
