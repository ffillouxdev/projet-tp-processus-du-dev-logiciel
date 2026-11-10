from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class TournamentConnectionManager:
    """Manages active WebSocket connections subscribed to tournament rooms."""

    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, tournament_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[tournament_id].add(websocket)

    def disconnect(self, tournament_id: int, websocket: WebSocket) -> None:
        if tournament_id in self._rooms:
            self._rooms[tournament_id].discard(websocket)
            if not self._rooms[tournament_id]:
                del self._rooms[tournament_id]

    async def broadcast_to_tournament(self, tournament_id: int, message: dict[str, Any]) -> None:
        if tournament_id not in self._rooms:
            return

        dead_connections: list[WebSocket] = []
        for ws in list(self._rooms[tournament_id]):
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)

        for ws in dead_connections:
            self.disconnect(tournament_id, ws)


# Global singleton instance for tournament broadcasting
tournament_connection_manager = TournamentConnectionManager()
