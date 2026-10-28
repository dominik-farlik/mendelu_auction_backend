from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws_manager import manager

ws_router = APIRouter(prefix="/ws")

@ws_router.websocket("/auctions/{product_id}")
async def auction_websocket(websocket: WebSocket, product_id: int):
    if not await manager.connect(websocket, product_id):
        return
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, product_id)
