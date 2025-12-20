import asyncio
import json
import logging
from nats.aio.client import Client as NATS
from typing import Dict, Any

logger = logging.getLogger(__name__)

class NatsClient:
    def __init__(self):
        self.nc = NATS()
        self.is_connected = False
        self.subscriptions = []
        
    async def connect(self, servers: str = "nats://localhost:4222"):
        try:
            await self.nc.connect(servers=servers)
            self.is_connected = True
            logger.info(f"NATS подключен: {servers}")
            await self.subscribe_to_channels()
        except Exception as e:
            logger.error(f"NATS ошибка подключения: {e}")
            self.is_connected = False
            
    async def subscribe_to_channels(self):
        try:
            sub = await self.nc.subscribe(
                "currency.updates", 
                cb=self.handle_message
            )
            self.subscriptions.append(sub)
            
        except Exception as e:
            logger.error(f"NATS ошибка подписки: {e}")
            
    async def handle_message(self, msg):
        try:
            data = json.loads(msg.data.decode())
            print(f"NATS команда: {data}")
        except Exception as e:
            print(f"NATS ошибка команды: {e}")
            
    async def publish(self, subject: str, payload: Dict[str, Any]):
        try:
            if not self.is_connected:
                return
            message = json.dumps(payload).encode()
            await self.nc.publish(subject, message)
        except Exception as e:
            logger.error(f"NATS ошибка публикации: {e}")
            
    async def disconnect(self):
        try:
            for sub in self.subscriptions:
                await sub.unsubscribe()
            await self.nc.close()
            self.is_connected = False
        except Exception as e:
            logger.error(f"NATS ошибка отключения: {e}")

nats_client = NatsClient()
