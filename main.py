from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
import json

app = FastAPI(title="Pigeon Messenger API", version="2.0")

# Хранилище активных соединений и открытых чатов
active_connections: dict[str, WebSocket] = {}
open_chats: dict[str, str] = {}  # username -> с кем открыт чат

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Обработка открытия чата
            if message.get("type") == "chat_opened":
                target = message.get("target")
                open_chats[username] = target
                # Уведомляем собеседника, что сообщения прочитаны
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "chat_opened_by",
                        "from": username
                    }))
                continue
            
            # Обработка статуса "прочитано"
            if message.get("type") == "read":
                target = message.get("target")
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "read",
                        "messageId": message.get("messageId"),
                        "from": username
                    }))
                continue
            
            # Обычное сообщение
            target = message.get("target")
            msg_id = message.get("id", str(hash(message.get("text", ""))))
            
            # Пересылаем сообщение получателю
            if target in active_connections:
                await active_connections[target].send_text(json.dumps({
                    "from": username,
                    "text": message.get("text", ""),
                    "id": msg_id,
                    "timestamp": message.get("timestamp")
                }))
            
            # Подтверждение отправки
            await websocket.send_text(json.dumps({
                "status": "sent",
                "id": msg_id
            }))
            
    except WebSocketDisconnect:
        if username in active_connections:
            del active_connections[username]
        if username in open_chats:
            del open_chats[username]

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "online": len(active_connections)}

# Статика
app.mount("/", StaticFiles(directory="static", html=True), name="static")