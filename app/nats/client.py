import asyncio
import json
import logging
from datetime import datetime  
from nats.aio.client import Client as NATS
from app.config import settings

logger = logging.getLogger(__name__)

class NatsClient:
    def __init__(self):
        self.nc = None
        self.connected = False
    
    async def connect(self):
        try:
            self.nc = NATS()
            await self.nc.connect(servers=settings.nats_url)
            self.connected = True
            logger.info(f"Connected to NATS at {settings.nats_url}")
        except Exception as e:
            logger.error(f"NATS connection failed: {e}")
            self.connected = False
    
    async def publish(self, subject: str, data: dict):
        if not self.connected or not self.nc:
            logger.warning("NATS not connected, skipping publish")
            return
        
        try:
            message = json.dumps(data)
            await self.nc.publish(subject, message.encode())
            logger.debug(f"Published to {subject}: {data}")
        except Exception as e:
            logger.error(f"Publish error: {e}")
    
    async def subscribe(self, subject: str, callback):
        if not self.connected or not self.nc:
            return
        
        try:
            await self.nc.subscribe(subject, cb=callback)
            logger.info(f"Subscribed to {subject}")
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
    
    async def close(self):
        if self.nc and self.connected:
            await self.nc.close()
            self.connected = False

nats_client = NatsClient()