from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging
from sqlalchemy import text, select 
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.parser import CurrencyParser
from app.db.database import AsyncSessionLocal
from app.db.models import Currency, CurrencyRate
from app.websocket.manager import manager
from app.nats.client import nats_client
from app.config import settings

logger = logging.getLogger(__name__)

class BackgroundTasks:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.parser = CurrencyParser()
        self.is_running = False
    
    async def update_currency_rates(self):
        logger.info("Запуск обновления курсов валют...")
        
        # Получаем данные
        rates = await self.parser.fetch_rates()
        
        async with AsyncSessionLocal() as session:
            for rate_data in rates:
                result = await session.execute(
                    select(Currency).where(Currency.code == rate_data['code'])
                )
                currency = result.scalar_one_or_none()
                
                if not currency:
                    # Создаем новую валюту
                    currency = Currency(
                        code=rate_data["code"],
                        name=rate_data["name"]
                    )
                    session.add(currency)
                    await session.commit()
                    await session.refresh(currency)
                
                # Добавляем курс
                rate = CurrencyRate(
                    currency_id=currency.id,
                    value=rate_data["value"],
                    date=datetime.now()
                )
                session.add(rate)
            
            await session.commit()
        
        # Отправляем в WebSocket
        await manager.broadcast({
            "type": "rates_updated",
            "data": rates,
            "timestamp": datetime.now().isoformat()
        })
        
        # Публикуем в NATS
        if hasattr(nats_client, 'connected') and nats_client.connected:
            await nats_client.publish(settings.nats_subject, {
                "event": "rates_updated",
                "data": rates
            })
        
        logger.info(f"Обновлено {len(rates)} валют")
    
    def start(self):
        if self.is_running:
            return
        
        self.scheduler.add_job(
            self.update_currency_rates,
            'interval',
            seconds=settings.update_interval,
            id='currency_update'
        )
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Фоновая задача запущена (интервал: {settings.update_interval}с)")
    
    async def manual_run(self):
        await self.update_currency_rates()

background_tasks = BackgroundTasks()