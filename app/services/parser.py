import httpx
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CurrencyParser:
    def __init__(self):
        self.api_url = "https://www.cbr-xml-daily.ru/daily_json.js"
    
    async def fetch_rates(self):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.api_url, timeout=10.0)
                data = response.json()
                
                rates = []
                for code, info in data["Valute"].items():
                    rates.append({
                        "code": code,
                        "name": info["Name"],
                        "value": info["Value"],
                        "previous": info["Previous"]
                    })
                
                logger.info(f"Получено {len(rates)} валют")
                return rates
                
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            return [
                {"code": "USD", "name": "Доллар США", "value": 75.5},
                {"code": "EUR", "name": "Евро", "value": 85.2},
            ]