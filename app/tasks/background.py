from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import logging
from app.services.parser import CurrencyParser
from app.db.database import AsyncSessionLocal
from app.websocket.manager import manager
from app.nats.client import nats_client

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def parse_and_save_rates():
    try:
        logger.info("Запуск автоматического парсинга...")
        
        async with AsyncSessionLocal() as db:
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
            
            if nats_client and nats_client.is_connected:
                await nats_client.publish(
                    subject="currency.updates",
                    payload={
                        "event": "auto_parse_completed",
                        "rates_count": saved_count,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            
            logger.info(f"Автопарсинг завершен. Курсов: {saved_count}")
            return saved_count
            
    except Exception as e:
        logger.error(f"Ошибка фоновой задачи: {e}")
        return 0

def start_background_scheduler():
    scheduler.remove_all_jobs()
    
    scheduler.add_job(
        parse_and_save_rates,
        'interval',
        minutes=10,
        id='auto_currency_parser',
        replace_existing=True
    )
    
    if not scheduler.running:
        scheduler.start()
        logger.info("Планировщик фоновых задач запущен")
    
    return scheduler
