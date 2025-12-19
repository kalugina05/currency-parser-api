from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class CurrencyBase(BaseModel):
    code: str
    name: str

class CurrencyCreate(CurrencyBase):
    pass

class CurrencyUpdate(BaseModel):  
    code: Optional[str] = None
    name: Optional[str] = None

class Currency(CurrencyBase):
    id: int
    class Config:
        from_attributes = True

class CurrencyRateBase(BaseModel):
    value: float

class CurrencyRate(CurrencyRateBase):
    id: int
    currency_id: int  
    date: datetime
    class Config:
        from_attributes = True

class CurrencyWithRates(Currency):
    rates: List[CurrencyRate] = []