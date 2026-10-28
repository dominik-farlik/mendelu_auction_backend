import logging

from fastapi import WebSocket
from typing import Dict, List

logger = logging.getLogger(__name__)

MAX_CONNECTIONS_PER_PRODUCT = 500


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, product_id: int) -> bool:
        connections = self.active_connections.get(product_id, [])
        if len(connections) >= MAX_CONNECTIONS_PER_PRODUCT:
            await websocket.close(code=1013)
            return False

        await websocket.accept()
        self.active_connections.setdefault(product_id, []).append(websocket)
        return True

    def disconnect(self, websocket: WebSocket, product_id: int):
        connections = self.active_connections.get(product_id)
        if connections is None:
            return
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            del self.active_connections[product_id]

    async def broadcast_to_product(self, message: dict, product_id: int):
        """Odešle JSON zprávu všem připojeným klientům u daného produktu."""
        # Kopie seznamu, protože se během await může měnit (připojení/odpojení klientů).
        for connection in list(self.active_connections.get(product_id, [])):
            try:
                await connection.send_json(message)
            except Exception as e:
                # Mrtvé spojení nesmí shodit request, který broadcast vyvolal (např. příhoz).
                logger.info(f"Removing dead websocket for product {product_id}: {e}")
                self.disconnect(connection, product_id)

manager = ConnectionManager()
