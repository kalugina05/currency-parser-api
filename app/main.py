from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import logging
import asyncio

from app.config import settings
from app.api.endpoints import router as api_router
from app.websocket.manager import manager
from app.tasks.background import background_tasks
from app.nats.client import nats_client
from app.db.database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск приложения...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await nats_client.connect()
    
    background_tasks.start()
    
    yield
    
    logger.info("Остановка приложения...")

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)

app.include_router(api_router)

@app.websocket("/ws/currencies")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "Подключено к обновлениям курсов"
        })
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket отключен")

@app.get("/")
async def root():
    return {
        "message": "Currency Parser API",
        "docs": "/docs",
        "websocket": "/ws/currencies"
    }