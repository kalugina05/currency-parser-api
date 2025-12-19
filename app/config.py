from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Currency Parser API"
    debug: bool = True
    database_url: str = "sqlite+aiosqlite:///./currency.db"
    nats_url: str = "nats://localhost:4222"
    nats_subject_updates: str = "currency.updates"
    nats_subject_external: str = "currency.external.updates"
    cbr_url: str = "http://www.cbr.ru/scripts/XML_daily.asp"
    background_task_interval: int = 600

settings = Settings()
