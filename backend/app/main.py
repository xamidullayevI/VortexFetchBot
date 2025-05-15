import os
import uuid
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import redis.asyncio as redis

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = FastAPI()

# CORS (frontend uchun)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redisga ulanish
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Foydalanuvchilarni matching qilish uchun navbat
def get_queue_key():
    return "anonymous_chat_queue"

def get_room_key(room_id):
    return f"chat_room:{room_id}"

# WebSocket ulanishi
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id = str(uuid.uuid4())
    await redis_client.rpush(get_queue_key(), user_id)
    try:
        # Matching kutish
        while True:
            # Navbatda boshqa foydalanuvchi bormi?
            queue = await redis_client.lrange(get_queue_key(), 0, -1)
            if len(queue) >= 2 and queue[0] == user_id:
                # Randomdan boshqa foydalanuvchini topamiz
                partner_id = queue[1]
                room_id = str(uuid.uuid4())
                await redis_client.set(f"user_room:{user_id}", room_id)
                await redis_client.set(f"user_room:{partner_id}", room_id)
                await redis_client.delete(get_queue_key())
                break
            await asyncio.sleep(1)
        # Room id topildi
        room_id = await redis_client.get(f"user_room:{user_id}")
        # Chat boshlanadi
        while True:
            data = await websocket.receive_text()
            await redis_client.rpush(get_room_key(room_id), f"{user_id}:{data}")
            # Xabarni boshqa foydalanuvchiga yuborish (broadcast)
            # (Frontend har 1s poll qiladi yoki WebSocket orqali xabar oladi)
    except WebSocketDisconnect:
        await redis_client.delete(f"user_room:{user_id}")
        await redis_client.lrem(get_queue_key(), 0, user_id)

# Chat xabarlarini olish uchun endpoint
@app.get("/chat/{room_id}/messages")
async def get_messages(room_id: str):
    messages = await redis_client.lrange(get_room_key(room_id), 0, -1)
    return {"messages": messages}

# Health check
default_root = "/"
@app.get(default_root)
async def root():
    return {"status": "ok"}
