from fastapi import FastAPI, WebSocket, HTTPException
from pydantic import BaseModel
from datetime import datetime
import asyncio
import json
import random

app = FastAPI(title="Currency Parser API")

class Currency(BaseModel):
    id: int
    code: str
    name: str
    rate: float = 0.0

class CurrencyCreate(BaseModel):
    code: str
    name: str

currencies_db = {}
next_id = 1
websocket_clients = []

@app.get("/")
async def root():
    return {"message": "Currency Parser API", "docs": "/docs", "websocket": "/ws/currencies"}

@app.get("/api/v1/currencies")
async def get_currencies():
    return list(currencies_db.values())

@app.get("/api/v1/currencies/{currency_id}")
async def get_currency(currency_id: int):
    if currency_id not in currencies_db:
        raise HTTPException(status_code=404, detail="Currency not found")
    return currencies_db[currency_id]

@app.post("/api/v1/currencies")
async def create_currency(currency: CurrencyCreate):
    global next_id
    new_currency = Currency(id=next_id, code=currency.code, name=currency.name, rate=75.0 + next_id)
    currencies_db[next_id] = new_currency.dict()
    next_id += 1
    
    for client in websocket_clients:
        try:
            await client.send_json({"type": "currency_created", "data": new_currency.dict(), "timestamp": datetime.now().isoformat()})
        except:
            continue
    
    return new_currency

@app.patch("/api/v1/currencies/{currency_id}")
async def update_currency(currency_id: int, updates: dict):
    if currency_id not in currencies_db:
        raise HTTPException(status_code=404, detail="Currency not found")
    
    for key, value in updates.items():
        if key in currencies_db[currency_id]:
            currencies_db[currency_id][key] = value
    
    for client in websocket_clients:
        try:
            await client.send_json({"type": "currency_updated", "data": currencies_db[currency_id], "timestamp": datetime.now().isoformat()})
        except:
            continue
    
    return currencies_db[currency_id]

@app.delete("/api/v1/currencies/{currency_id}")
async def delete_currency(currency_id: int):
    if currency_id not in currencies_db:
        raise HTTPException(status_code=404, detail="Currency not found")
    
    del currencies_db[currency_id]
    
    for client in websocket_clients:
        try:
            await client.send_json({"type": "currency_deleted", "data": {"id": currency_id}, "timestamp": datetime.now().isoformat()})
        except:
            continue
    
    return {"message": "Currency deleted", "id": currency_id}

@app.post("/api/v1/tasks/run")
async def run_task():
    demo_rates = [
        {"code": "USD", "rate": 75.5 + random.uniform(-1, 1)},
        {"code": "EUR", "rate": 85.2 + random.uniform(-1, 1)},
        {"code": "GBP", "rate": 95.0 + random.uniform(-1, 1)}
    ]
    
    for client in websocket_clients:
        try:
            await client.send_json({"type": "rates_updated", "data": demo_rates, "timestamp": datetime.now().isoformat()})
        except:
            continue
    
    return {"message": "Background task started", "updated_rates": len(demo_rates), "timestamp": datetime.now().isoformat()}

@app.websocket("/ws/currencies")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    websocket_clients.append(websocket)
    
    try:
        await websocket.send_json({"type": "connected", "message": "Connected to currency updates", "timestamp": datetime.now().isoformat()})
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                
    except:
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
