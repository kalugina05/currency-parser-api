from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

class Currency(Base):
    __tablename__ = "currencies"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(3), unique=True, index=True)  
    name = Column(String(100))
    rates = relationship("CurrencyRate", back_populates="currency")

class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    id = Column(Integer, primary_key=True, index=True)
    currency_id = Column(Integer, ForeignKey("currencies.id"))
    value = Column(Float)
    date = Column(DateTime, default=datetime.now)
    currency = relationship("Currency", back_populates="rates")