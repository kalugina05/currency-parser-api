# Currency Parser API

Асинхронный backend-сервис на FastAPI с WebSocket, NATS и фоновыми задачами для парсинга курсов валют ЦБ РФ.

## Требования задания

✅ **REST API** - CRUD операции для валют  
✅ **WebSocket** - real-time уведомления  
✅ **Фоновая задача** - парсинг данных каждые 60 секунд через httpx  
✅ **Принудительный запуск** задачи через API  
✅ **NATS** - брокер сообщений для событий  
✅ **Асинхронная БД** - SQLite через SQLAlchemy  

## Быстрый старт

### Docker 
```bash
# Запустить 
docker-compose up -d

# Проверить работу
docker-compose ps

# Остановить
docker-compose down