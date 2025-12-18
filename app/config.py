from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Currency API"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./currency.db"
    nats_url: str = "nats://localhost:4222"
    nats_subject: str = "currency.updates"
    cbr_url: str = "https://www.cbr-xml-daily.ru/daily_json.js"
    update_interval: int = 60  
    
settings = Settings()