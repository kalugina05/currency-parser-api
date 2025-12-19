import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import Currency, CurrencyRate

logger = logging.getLogger(__name__)

class CurrencyParser:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cbr_url = "http://www.cbr.ru/scripts/XML_daily.asp"
        
    async def fetch_rates(self):
        """Получает курсы валют с сайта ЦБ РФ"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Получаем XML с курсами на сегодня
                response = await client.get(self.cbr_url)
                response.raise_for_status()
                
                # Парсим XML
                root = ET.fromstring(response.text)
                rates = []
                
                for valute in root.findall('Valute'):
                    code = valute.find('CharCode').text
                    name = valute.find('Name').text
                    value_str = valute.find('Value').text.replace(',', '.')
                    nominal = int(valute.find('Nominal').text)
                    
                    # Вычисляем курс за 1 единицу валюты
                    value = float(value_str) / nominal
                    
                    rates.append({
                        "code": code,
                        "name": name,
                        "rate": value
                    })
                    
                logger.info(f"Получено {len(rates)} курсов валют с ЦБ РФ")
                return rates
                
        except httpx.TimeoutException:
            logger.error("Таймаут при подключении к ЦБ РФ")
            raise Exception("Не удалось подключиться к серверу ЦБ РФ (таймаут)")
        except httpx.RequestError as e:
            logger.error(f"Ошибка сети при подключении к ЦБ РФ: {e}")
            raise Exception(f"Ошибка сети: {e}")
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML от ЦБ РФ: {e}")
            raise Exception("Некорректный ответ от сервера ЦБ РФ")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении курсов: {e}")
            raise Exception(f"Ошибка при получении данных: {e}")
    
    async def save_rates(self, rates):
        """Сохраняет курсы валют в базу данных"""
        if not rates:
            raise ValueError("Нет данных для сохранения")
            
        saved_count = 0
        
        for rate_data in rates:
            # Ищем валюту по коду
            result = await self.db.execute(
                select(Currency).where(Currency.code == rate_data["code"])
            )
            currency = result.scalar_one_or_none()
            
            # Если валюты нет - создаём
            if not currency:
                currency = Currency(
                    code=rate_data["code"],
                    name=rate_data["name"]
                )
                self.db.add(currency)
                await self.db.commit()
                await self.db.refresh(currency)
            
            # Создаём запись о курсе
            currency_rate = CurrencyRate(
                currency_id=currency.id,
                value=rate_data["rate"],
                date=datetime.now()
            )
            self.db.add(currency_rate)
            saved_count += 1
        
        await self.db.commit()
        logger.info(f"Сохранено {saved_count} курсов валют")
        return saved_count
