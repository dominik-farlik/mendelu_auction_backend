from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws_manager import manager

ws_router = APIRouter(prefix="/ws")

@ws_router.websocket("/auctions/{product_id}")
async def auction_websocket(websocket: WebSocket, product_id: int):
    await manager.connect(websocket, product_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, product_id)