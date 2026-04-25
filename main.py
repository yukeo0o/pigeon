from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
from database import create_user, check_user, update_profile, get_profile

app = FastAPI(title="Pigeon Messenger API", version="2.0")

active_connections: dict[str, WebSocket] = {}
open_chats: dict[str, str] = {}

# Модели запросов
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class ProfileUpdate(BaseModel):
    username: str
    first_name: str = ""
    last_name: str = ""
    nickname: str = ""

# API: Регистрация
@app.post("/api/register")
async def register(req: RegisterRequest):
    user = create_user(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    return {"status": "ok", "username": user.username}

# API: Вход
@app.post("/api/login")
async def login(req: LoginRequest, response: Response):
    if check_user(req.username, req.password):
        # Создаём "штамп" (cookie) на 30 дней
        from datetime import datetime, timedelta
        import jwt  # Не забудь добавить PyJWT в requirements.txt
        token = jwt.encode(
            {"username": req.username, "exp": datetime.utcnow() + timedelta(days=30)},
            "pigeon_secret_key", 
            algorithm="HS256"
        )
        response.set_cookie(key="pigeon_session", value=token, max_age=2592000)
        return {"status": "ok", "username": req.username}
    raise HTTPException(status_code=401, detail="Неверный логин или пароль")

# API: Профиль
@app.get("/api/profile/{username}")
async def get_user_profile(username: str):
    return get_profile(username)

@app.put("/api/profile")
async def update_user_profile(req: ProfileUpdate):
    update_profile(req.username, req.first_name, req.last_name, req.nickname)
    return {"status": "ok"}

# WebSocket
@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "friend_request":
                target = message.get("target")
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "friend_request", "from": username
                    }))
                continue

            if msg_type == "accept_friend":
                target = message.get("target")
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "friend_accepted", "from": username
                    }))
                continue

            if msg_type == "chat_opened":
                target = message.get("target")
                open_chats[username] = target
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "chat_opened_by", "from": username
                    }))
                continue

            if msg_type == "read":
                target = message.get("target")
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "read", "messageId": message.get("messageId"), "from": username
                    }))
                continue

            if msg_type == "reaction":
                target = message.get("target")
                if target in active_connections:
                    await active_connections[target].send_text(json.dumps({
                        "type": "reaction", "messageId": message.get("messageId"),
                        "reaction": message.get("reaction"), "from": username
                    }))
                continue

            # Обычное сообщение
            target = message.get("target")
            msg_id = message.get("id", str(hash(message.get("text", ""))))

            if target in active_connections:
                await active_connections[target].send_text(json.dumps({
                    "from": username, "text": message.get("text", ""),
                    "id": msg_id, "timestamp": message.get("timestamp")
                }))

            await websocket.send_text(json.dumps({"status": "sent", "id": msg_id}))

    except WebSocketDisconnect:
        if username in active_connections:
            del active_connections[username]
        if username in open_chats:
            del open_chats[username]

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "online": len(active_connections)}

app.mount("/", StaticFiles(directory="static", html=True), name="static")
