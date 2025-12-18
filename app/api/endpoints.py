from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from typing import List

from app.db.database import get_db
from app.db.models import Currency, CurrencyRate
from app.api.schemas import Currency as CurrencySchema, CurrencyCreate, CurrencyUpdate, CurrencyRate as CurrencyRateSchema
from app.tasks.background import background_tasks
from app.websocket.manager import manager
from app.nats.client import nats_client

router = APIRouter(prefix="/api/v1")

@router.get("/currencies", response_model=List[CurrencySchema])
async def get_currencies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Currency))
    return result.scalars().all()

@router.get("/currencies/{currency_id}", response_model=CurrencySchema)
async def get_currency(currency_id: int, db: AsyncSession = Depends(get_db)):
    currency = await db.get(Currency, currency_id)
    if not currency:
        raise HTTPException(404, "Валюта не найдена")
    return currency

@router.post("/currencies", response_model=CurrencySchema)
async def create_currency(currency: CurrencyCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Currency).where(Currency.code == currency.code)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(400, f"Валюта с кодом {currency.code} уже существует")
    
    db_currency = Currency(**currency.dict())
    db.add(db_currency)
    await db.commit()
    await db.refresh(db_currency)
    return db_currency

@router.patch("/currencies/{currency_id}", response_model=CurrencySchema) 
async def update_currency(
    currency_id: int,
    currency_update: CurrencyUpdate,
    db: AsyncSession = Depends(get_db)
):

    currency = await db.get(Currency, currency_id)
    if not currency:
        raise HTTPException(404, "Валюта не найдена")
    
    update_data = currency_update.dict(exclude_unset=True)
    
    if "code" in update_data:
        if update_data["code"] != currency.code:
            result = await db.execute(
                select(Currency).where(Currency.code == update_data["code"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(400, f"Код {update_data['code']} уже используется")
    
    for field, value in update_data.items():
        setattr(currency, field, value)
    
    await db.commit()
    await db.refresh(currency)
    
    await manager.broadcast({
        "type": "currency_updated",
        "data": CurrencySchema.from_orm(currency).dict(),
        "timestamp": datetime.now().isoformat()
    })
    
    if hasattr(nats_client, 'connected') and nats_client.connected:
        await nats_client.publish(
            "currency.updates",
            {
                "event": "currency_updated",
                "payload": CurrencySchema.from_orm(currency).dict(),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    return currency

@router.delete("/currencies/{currency_id}")
async def delete_currency(currency_id: int, db: AsyncSession = Depends(get_db)):
    currency = await db.get(Currency, currency_id)
    if not currency:
        raise HTTPException(404, "Валюта не найдена")
    
    await db.delete(currency)
    await db.commit()
    
    await manager.broadcast({
        "type": "currency_deleted",
        "data": {"id": currency_id},
        "timestamp": datetime.now().isoformat()
    })
    
    return {"message": "Валюта удалена"}

@router.get("/rates", response_model=List[CurrencyRateSchema])
async def get_rates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CurrencyRate))
    return result.scalars().all()

@router.post("/tasks/run")
async def run_task():
    await background_tasks.manual_run()
    return {"message": "Фоновая задача запущена вручную"}