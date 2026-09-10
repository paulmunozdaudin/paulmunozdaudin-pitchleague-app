"""In-process WebSocket fanout for league rooms. Deliberately simple (a
dict of live connections, no external pub/sub) — enough for a single
backend instance; the natural upgrade path if we ever run more than one
worker is Supabase Realtime or a Redis-backed pub/sub, swapped in behind
this same `broadcast` call. See docs/ARCHITECTURE.md#realtime."""

import uuid
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, league_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[league_id].add(websocket)

    def disconnect(self, league_id: uuid.UUID, websocket: WebSocket) -> None:
        self._rooms[league_id].discard(websocket)

    async def broadcast(self, league_id: uuid.UUID, event: dict) -> None:
        dead = []
        for websocket in self._rooms.get(league_id, set()):
            try:
                await websocket.send_json(event)
            except Exception:  # noqa: BLE001 — drop connections that fail to send
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(league_id, websocket)


manager = ConnectionManager()
