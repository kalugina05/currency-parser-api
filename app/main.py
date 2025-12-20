from fastapi import FastAPI, WebSocket, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.db.models import Currency, CurrencyRate
from app.api.schemas import CurrencyCreate, CurrencyUpdate
from app.websocket.manager import manager
from app.nats.client import nats_client
from app.tasks.background import scheduler, start_background_scheduler
from datetime import datetime
import logging

app = FastAPI(title="Currency Parser API")
logger = logging.getLogger(__name__)

websocket_clients = []

@app.on_event("startup")
async def startup():
    print("=== STARTUP FUNCTION EXECUTED ===")
    try:
        from app.db.database import engine, Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("1. Таблицы БД созданы")
        logger.info("Таблицы БД созданы")
        
        from app.config import settings
        print("2. Подключение к NATS...")
        await nats_client.connect(settings.nats_url)
        
        print("3. Запуск фоновых задач...")
        start_background_scheduler()
        logger.info("Фоновые задачи запущены")
        
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        logger.error(f"Ошибка запуска: {e}")

@app.on_event("shutdown")
async def shutdown():
    try:
        await nats_client.disconnect()
        if scheduler.running:
            scheduler.shutdown()
        logger.info("Приложение завершено")
    except Exception as e:
        logger.error(f"Ошибка завершения: {e}")


@app.get("/api/v1/currencies")
async def get_currencies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Currency))
    currencies = result.scalars().all()
    return currencies

@app.get("/api/v1/currencies/{currency_id}")
async def get_currency(currency_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Currency).where(Currency.id == currency_id)
    )
    currency = result.scalar_one_or_none()

    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")
    return currency

@app.post("/api/v1/currencies")
async def create_currency(currency_data: CurrencyCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Currency).where(Currency.code == currency_data.code)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail=f"Currency {currency_data.code} already exists")
    
    db_currency = Currency(
        code=currency_data.code,
        name=currency_data.name
    )
    db.add(db_currency)
    await db.commit()
    await db.refresh(db_currency)

    await manager.broadcast({
        "type": "currency_created",
        "data": {
            "id": db_currency.id,
            "code": db_currency.code,
            "name": db_currency.name
        },
        "timestamp": datetime.now().isoformat()
    })

    if nats_client.is_connected:
        await nats_client.publish(
            subject="currency.updates",
            payload={
                "event": "currency_created",
                "currency_id": db_currency.id,
                "code": db_currency.code,
                "timestamp": datetime.now().isoformat()
            }
        )

    return db_currency

@app.patch("/api/v1/currencies/{currency_id}")
async def update_currency(
    currency_id: int,
    updates: CurrencyUpdate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Currency).where(Currency.id == currency_id)
    )
    currency = result.scalar_one_or_none()

    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(currency, field, value)

    await db.commit()
    await db.refresh(currency)

    await manager.broadcast({
        "type": "currency_updated",
        "data": {
            "id": currency.id,
            "code": currency.code,
            "name": currency.name
        },
        "timestamp": datetime.now().isoformat()
    })

    if nats_client.is_connected:
        await nats_client.publish(
            subject="currency.updates",
            payload={
                "event": "currency_updated",
                "currency_id": currency.id,
                "code": currency.code,
                "timestamp": datetime.now().isoformat()
            }
        )

    return currency

@app.delete("/api/v1/currencies/{currency_id}")
async def delete_currency(currency_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Currency).where(Currency.id == currency_id)
    )
    currency = result.scalar_one_or_none()

    if not currency:
        raise HTTPException(status_code=404, detail="Currency not found")

    await db.delete(currency)
    await db.commit()

    await manager.broadcast({
        "type": "currency_deleted",
        "data": {"id": currency_id},
        "timestamp": datetime.now().isoformat()
    })

    if nats_client.is_connected:
        await nats_client.publish(
            subject="currency.updates",
            payload={
                "event": "currency_deleted",
                "currency_id": currency_id,
                "timestamp": datetime.now().isoformat()
            }
        )

    return {"message": "Currency deleted", "id": currency_id}

@app.post("/api/v1/tasks/run")
async def run_task(db: AsyncSession = Depends(get_db)):
    from app.services.parser import CurrencyParser
    
    try:
        parser = CurrencyParser(db)
        rates = await parser.fetch_rates()
        saved_count = await parser.save_rates(rates)
        
        await manager.broadcast({
            "type": "rates_updated",
            "data": {
                "rates_count": saved_count,
                "timestamp": datetime.now().isoformat()
            }
        })
        
        if nats_client.is_connected:
            await nats_client.publish(
                subject="currency.updates",
                payload={
                    "event": "manual_parse_completed",
                    "rates_count": saved_count,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        return {
            "message": "Курсы получены",
            "currencies_updated": saved_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Ошибка run_task: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

@app.websocket("/ws/currencies")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket подключен",
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                
    except Exception as e:
        logger.error(f"WebSocket ошибка: {e}")
    finally:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
