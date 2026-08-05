from fastapi import WebSocket
from typing import Dict, List

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, product_id: int):
        await websocket.accept()
        if product_id not in self.active_connections:
            self.active_connections[product_id] = []
        self.active_connections[product_id].append(websocket)

    def disconnect(self, websocket: WebSocket, product_id: int):
        if product_id in self.active_connections:
            self.active_connections[product_id].remove(websocket)
            if not self.active_connections[product_id]:
                del self.active_connections[product_id]

    async def broadcast_to_product(self, message: dict, product_id: int):
        """Odešle JSON zprávu všem připojeným klientům u daného produktu."""
        if product_id in self.active_connections:
            for connection in self.active_connections[product_id]:
                await connection.send_json(message)

manager = ConnectionManager()