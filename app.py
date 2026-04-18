import streamlit as st
import json
from pathlib import Path
from datetime import datetime, timedelta
import extra_streamlit_components as stx
import time
import pandas as pd
import base64
from PIL import Image
import io
import hashlib
from streamlit_autorefresh import st_autorefresh
import pytz
import asyncio
import websockets
import threading
import queue

# WebSocket клиент
ws_queue = queue.Queue()
ws_connected = False
ws_client_id = None

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# Подключение шрифта Noto Sans
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans', sans-serif;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

@keyframes typing {
    0% { content: '.'; }
    33% { content: '..'; }
    66% { content: '...'; }
    100% { content: '.'; }
}

.typing-indicator {
    display: inline-block;
    color: #666;
    font-style: italic;
    animation: pulse 1.5s infinite;
}.notification-bubble {
    background: #E8D5F5;
    color: #000000;
    padding: 12px;
    border-radius: 12px;
    margin: 5px 0;
    border-left: 4px solid #7B2D8E;
}

.typing-dots::after {
    content: '';
    animation: typing 1.5s infinite;
}

.online-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    background-color: #4CAF50;
    border-radius: 50%;
    margin-right: 5px;
    animation: pulse 2s infinite;
}

.offline-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    background-color: #999;
    border-radius: 50%;
    margin-right: 5px;
}

.message-bubble {
    word-wrap: break-word;
    overflow-wrap: break-word;
    word-break: break-word;
}
</style>
""", unsafe_allow_html=True)

# Файлы
MESSAGES_FILE = Path("messages/messages.json")
USERS_FILE = Path("users/users.json")
CONTACTS_FILE = Path("users/contacts.json")
GROUPS_FILE = Path("users/groups.json")
FRIEND_REQUESTS_FILE = Path("users/friend_requests.json")
ONLINE_STATUS_FILE = Path("users/online_status.json")

# Создаем папки
Path("messages").mkdir(exist_ok=True)
Path("users").mkdir(exist_ok=True)
Path("messages/photos").mkdir(parents=True, exist_ok=True)

# Московское время
MSK_TZ = pytz.timezone('Europe/Moscow')

def get_msk_time():
    return datetime.now(MSK_TZ)

def format_last_seen(timestamp_str):
    if not timestamp_str:
        return "никогда не был"
    
    last_seen = datetime.fromisoformat(timestamp_str)
    now = get_msk_time()
    diff = now - last_seen
    
    if diff < timedelta(minutes=1):
        return "только что"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} мин назад"
    elif diff < timedelta(hours=24):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} ч назад"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} дн назад"
    else:
        return last_seen.strftime("%d.%m.%Y")

# Куки
cookie_manager = stx.CookieManager()
time.sleep(0.8)

if "logged_user" not in st.session_state:
    saved_user = cookie_manager.get(cookie="pigeon_user_v10")
    if saved_user:
        st.session_state["logged_user"] = saved_user
    else:
        st.session_state["logged_user"] = None

if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

if "chat_type" not in st.session_state:
    st.session_state["chat_type"] = "private"

if "current_menu" not in st.session_state:
    st.session_state["current_menu"] = "chats"

# Автообновление только в чате
if st.session_state.get("logged_user") and st.session_state.get("selected_chat"):
    st_autorefresh(interval=2000, limit=100000, debounce=True)

# Проверяем WebRTC
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False

# --- WebSocket функции ---
async def connect_websocket(username):
    global ws_connected, ws_queue
    uri = f"ws://127.0.0.1:8000/ws/{username}"
    try:
        async with websockets.connect(uri) as websocket:
            ws_connected = True
            
            async def send_messages():
                while True:
                    try:
                        msg = ws_queue.get_nowait()
                        await websocket.send(msg)
                    except queue.Empty:
                        await asyncio.sleep(0.1)
            
            async def receive_messages():
                async for message in websocket:
                    st.session_state["new_ws_message"] = message
                    st.rerun()
            
            await asyncio.gather(send_messages(), receive_messages())
    except:
        ws_connected = False

def start_websocket(username):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_websocket(username))

# --- ФУНКЦИИ БЕЗОПАСНОСТИ ---
def hash_password(password):
    salt = "pigeon_salt_2024"
    return hashlib.sha256((password + salt).encode()).hexdigest()

def check_password(username, password):
    users = load_users()
    if username in users:
        return users[username].get("password") == hash_password(password)
    return False

# --- ОНЛАЙН СТАТУС ---
def update_online_status(username):
    status = load_online_status()
    status[username] = {
        "last_seen": get_msk_time().isoformat(),
        "is_online": True
    }
    with open(ONLINE_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False)

def load_online_status():
    if ONLINE_STATUS_FILE.exists():
        with open(ONLINE_STATUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def is_user_online(username):
    status = load_online_status()
    if username in status:
        last_seen = datetime.fromisoformat(status[username]["last_seen"])
        now = get_msk_time()
        return (now - last_seen) < timedelta(minutes=2)
    return False

def get_user_last_seen(username):
    status = load_online_status()
    if username in status:
        return status[username]["last_seen"]
    return None

# --- СТАТУС ПЕЧАТАЕТ ---
def update_typing_status(sender, target, is_typing):
    typing_file = Path("users/typing_status.json")
    if typing_file.exists():
        with open(typing_file, 'r', encoding='utf-8') as f:
            typing_data = json.load(f)
    else:
        typing_data = {}
    
    key = f"{sender}_{target}"
    typing_data[key] = {
        "is_typing": is_typing,
        "timestamp": get_msk_time().isoformat()
    }
    
    with open(typing_file, 'w', encoding='utf-8') as f:
        json.dump(typing_data, f, ensure_ascii=False)

def is_user_typing(sender, target):
    typing_file = Path("users/typing_status.json")
    if typing_file.exists():
        with open(typing_file, 'r', encoding='utf-8') as f:
            typing_data = json.load(f)
        key = f"{sender}_{target}"
        if key in typing_data:
            data = typing_data[key]
            if data["is_typing"]:
                timestamp = datetime.fromisoformat(data["timestamp"])
                if (get_msk_time() - timestamp) < timedelta(seconds=5):
                    return True
    return False

# --- РАБОТА С ДАННЫМИ ---
def load_messages():
    if MESSAGES_FILE.exists():
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_message(sender, target, text, msg_type="text", chat_type="private"):
    msgs = load_messages()
    msgs.append({
        "sender": sender,
        "target": target,
        "text": text,
        "type": msg_type,
        "chat_type": chat_type,
        "time": get_msk_time().strftime("%H:%M"),
        "timestamp": get_msk_time().isoformat()
    })
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False)
    update_typing_status(sender, target, False)
    
    # Отправляем через WebSocket
    if ws_connected:
        msg_data = json.dumps({
            "sender": sender,
            "target": target,
            "text": text,
            "type": msg_type,
            "chat_type": chat_type
        })
        ws_queue.put(msg_data)

def save_photo(sender, target, photo_bytes, chat_type="private"):
    photo_dir = Path("messages/photos")
    photo_name = f"{get_msk_time().strftime('%Y%m%d_%H%M%S')}_{sender}.jpg"
    photo_path = photo_dir / photo_name
    
    img = Image.open(io.BytesIO(photo_bytes))
    img.save(photo_path)
    
    msgs = load_messages()
    msgs.append({
        "sender": sender,
        "target": target,
        "type": "photo",
        "photo_path": str(photo_path),
        "chat_type": chat_type,
        "time": get_msk_time().strftime("%H:%M"),
        "timestamp": get_msk_time().isoformat()
    })
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False)

def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user(username, password):
    users = load_users()
    if username not in users:
        users[username] = {
            "created": get_msk_time().isoformat(),
            "password": hash_password(password),
            "bio": "",
            "phone": ""
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False)
        return True
    return False

def load_contacts(username):
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            all_contacts = json.load(f)
            return all_contacts.get(username, [])
    return []

def save_contact(username, contact):
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            all_contacts = json.load(f)
    else:
        all_contacts = {}
    
    if username not in all_contacts:
        all_contacts[username] = []
    
    if contact not in all_contacts[username]:
        all_contacts[username].append(contact)
        with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_contacts, f, ensure_ascii=False)
        return True
    return False

def remove_contact(username, contact):
    if CONTACTS_FILE.exists():
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            all_contacts = json.load(f)
        if username in all_contacts and contact in all_contacts[username]:
            all_contacts[username].remove(contact)
            with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(all_contacts, f, ensure_ascii=False)

def load_friend_requests():
    if FRIEND_REQUESTS_FILE.exists():
        with open(FRIEND_REQUESTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def send_friend_request(from_user, to_user):
    requests = load_friend_requests()
    if to_user not in requests:
        requests[to_user] = []
    if from_user not in requests[to_user]:
        requests[to_user].append(from_user)
        with open(FRIEND_REQUESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(requests, f, ensure_ascii=False)
        return True
    return False

def accept_friend_request(from_user, to_user):
    requests = load_friend_requests()
    if to_user in requests and from_user in requests[to_user]:
        requests[to_user].remove(from_user)
        with open(FRIEND_REQUESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(requests, f, ensure_ascii=False)
    save_contact(from_user, to_user)
    save_contact(to_user, from_user)

def decline_friend_request(from_user, to_user):
    requests = load_friend_requests()
    if to_user in requests and from_user in requests[to_user]:
        requests[to_user].remove(from_user)
        with open(FRIEND_REQUESTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(requests, f, ensure_ascii=False)

def get_pending_requests(username):
    requests = load_friend_requests()
    return requests.get(username, [])

def is_friend_request_sent(from_user, to_user):
    requests = load_friend_requests()
    return from_user in requests.get(to_user, [])

def load_groups():
    if GROUPS_FILE.exists():
        with open(GROUPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_group(group_name, creator, members):
    groups = load_groups()
    groups[group_name] = {
        "creator": creator,
        "members": members,
        "created": get_msk_time().isoformat()
    }
    with open(GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump(groups, f, ensure_ascii=False)

def get_user_groups(username):
    groups = load_groups()
    user_groups = []
    for group_name, group_data in groups.items():
        if username in group_data["members"]:
            user_groups.append(group_name)
    return user_groups

def get_last_message(user, target, chat_type="private"):
    msgs = load_messages()
    if chat_type == "private":
        chat_msgs = [m for m in msgs if (m["sender"] == user and m["target"] == target) or 
                     (m["sender"] == target and m["target"] == user)]
    else:
        chat_msgs = [m for m in msgs if m.get("target") == target and m.get("chat_type") == "group"]
    
    if chat_msgs:
        last = chat_msgs[-1]
        if last.get("type") == "photo":
            return f"{last['sender']}: 📷 Фото"
        return f"{last['sender']}: {last['text'][:30]}..."
    return "Нет сообщений"

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("🕊️ Pigeon")
        st.subheader("Вход / Регистрация")
        
        tab1, tab2 = st.tabs(["🚪 Войти", "✨ Регистрация"])
        
        with tab1:
            login_name = st.text_input("Логин", key="login")
            login_password = st.text_input("Пароль", type="password", key="login_pass")
            
            if st.button("🚀 Войти", use_container_width=True):
                if login_name and login_password:
                    if check_password(login_name, login_password):
                        st.session_state["logged_user"] = login_name
                        cookie_manager.set("pigeon_user_v10", login_name, expires_at=datetime.now() + pd.Timedelta(days=30))
                        update_online_status(login_name)
                        # Запускаем WebSocket
                        if not ws_connected:
                            threading.Thread(target=start_websocket, args=(login_name,), daemon=True).start()
                        st.success("Успешный вход!")
                        st.rerun()
                    else:
                        st.error("Неверный логин или пароль")
                else:
                    st.warning("Введите логин и пароль")
        
        with tab2:
            reg_name = st.text_input("Придумайте логин", key="reg")
            reg_password = st.text_input("Придумайте пароль", type="password", key="reg_pass")
            reg_password2 = st.text_input("Повторите пароль", type="password", key="reg_pass2")
            
            if st.button("✨ Зарегистрироваться", use_container_width=True):
                if not reg_name or not reg_password:
                    st.warning("Заполните все поля")
                elif reg_password != reg_password2:
                    st.error("Пароли не совпадают")
                elif len(reg_password) < 4:
                    st.error("Пароль должен быть не менее 4 символов")
                elif reg_name in load_users():
                    st.error("Пользователь с таким логином уже существует")
                else:
                    if save_user(reg_name, reg_password):
                        st.session_state["logged_user"] = reg_name
                        cookie_manager.set("pigeon_user_v10", reg_name, expires_at=datetime.now() + pd.Timedelta(days=30))
                        update_online_status(reg_name)
                        # Запускаем WebSocket
                        if not ws_connected:
                            threading.Thread(target=start_websocket, args=(reg_name,), daemon=True).start()
                        st.success("Регистрация успешна!")
                        st.rerun()
        
        st.divider()
        st.caption(f"👥 Пользователей: {len(load_users())}")
    
    else:
        curr = st.session_state["logged_user"]
        update_online_status(curr)
        
        # Шапка
        st.markdown(f"### 🕊️ {curr}")
        
        # Поиск
        search = st.text_input("🔍 Поиск", placeholder="Найти чат или контакт...", label_visibility="collapsed")
        
        st.divider()
        
        # Кнопка создания
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("➕", help="Создать группу", use_container_width=True):
                st.session_state["show_create_group"] = True
        
        # Список чатов
        st.subheader("💬 Чаты")
        
        contacts = load_contacts(curr)
        groups = get_user_groups(curr)
        
        if search:
            contacts = [c for c in contacts if search.lower() in c.lower()]
            groups = [g for g in groups if search.lower() in g.lower()]
        
        # Заявки в друзья
        pending = get_pending_requests(curr)
        if pending:
            with st.expander(f"📬 Заявки ({len(pending)})", expanded=False):
                for req in pending:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                            st.markdown(f'<div class="notification-bubble">🕊️ <b>{req}</b> хочет добавиться в друзья</div>', unsafe_allow_html=True)
                    with col2:
                        if st.button("✅", key=f"acc_{req}"):
                            accept_friend_request(req, curr)
                            st.rerun()
                    with col3:
                        if st.button("❌", key=f"dec_{req}"):
                            decline_friend_request(req, curr)
                            st.rerun()
        
        # Отображаем чаты
        if contacts:
            for contact in contacts:
                last_msg = get_last_message(curr, contact, "private")
                is_online = is_user_online(contact)
                status_dot = "🟢" if is_online else "⚪"
                
                if st.button(f"{status_dot} {contact}\n_{last_msg}_", key=f"chat_{contact}", use_container_width=True):
                    st.session_state["selected_chat"] = contact
                    st.session_state["chat_type"] = "private"
                    st.rerun()
        
        if groups:
            for group in groups:
                last_msg = get_last_message(curr, group, "group")
                
                if st.button(f"👥 {group}\n_{last_msg}_", key=f"grp_{group}", use_container_width=True):
                    st.session_state["selected_chat"] = group
                    st.session_state["chat_type"] = "group"
                    st.rerun()
        
        if not contacts and not groups:
            st.caption("Нет чатов. Нажмите 🔍 чтобы найти друзей.")
        
        st.divider()
        
        # Кнопка "Ещё"
        with st.expander("⚙️ Ещё", expanded=False):
            if st.button("👤 Профиль", use_container_width=True):
                st.session_state["current_menu"] = "profile"
                st.rerun()
            if st.button("👥 Контакты", use_container_width=True):
                st.session_state["current_menu"] = "contacts"
                st.rerun()
            if st.button("🔍 Найти людей", use_container_width=True):
                st.session_state["current_menu"] = "search"
                st.rerun()
            if st.button("🚪 Выйти", use_container_width=True):
                cookie_manager.delete("pigeon_user_v10")
                st.session_state["logged_user"] = None
                st.session_state["selected_chat"] = None
                st.rerun()

# --- ОКНО СОЗДАНИЯ ГРУППЫ ---
if st.session_state.get("show_create_group", False):
    with st.sidebar:
        st.subheader("➕ Создать группу")
        group_name = st.text_input("Название группы")
        all_users = list(load_users().keys())
        if curr in all_users:
            all_users.remove(curr)
        selected = st.multiselect("Участники", all_users)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Создать", use_container_width=True):
                if group_name and selected:
                    save_group(group_name, curr, [curr] + selected)
                    st.success("Группа создана!")
                    st.session_state["show_create_group"] = False
                    st.rerun()
        with col2:
            if st.button("Отмена", use_container_width=True):
                st.session_state["show_create_group"] = False
                st.rerun()

# --- ЭКРАНЫ МЕНЮ "ЕЩЁ" ---
if st.session_state.get("current_menu") == "profile":
    st.header("👤 Профиль")
    users = load_users()
    user_data = users.get(curr, {})
    
    st.write(f"**Логин:** {curr}")
    st.write(f"**Дата регистрации:** {user_data.get('created', 'Неизвестно')[:10]}")
    
    msgs = load_messages()
    sent = len([m for m in msgs if m["sender"] == curr])
    received = len([m for m in msgs if m.get("target") == curr])
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📤 Отправлено", sent)
    with col2:
        st.metric("📥 Получено", received)
    
    if st.button("← Назад"):
        st.session_state["current_menu"] = "chats"
        st.rerun()

elif st.session_state.get("current_menu") == "contacts":
    st.header("👥 Мои контакты")
    contacts = load_contacts(curr)
    if contacts:
        for contact in contacts:
            is_online = is_user_online(contact)
            status_dot = "🟢" if is_online else "⚪"
            last_seen = get_user_last_seen(contact)
            last_seen_text = "онлайн" if is_online else format_last_seen(last_seen)
            st.write(f"{status_dot} 🕊️ **{contact}** — {last_seen_text}")
    else:
        st.info("Список контактов пуст")
    
    if st.button("← Назад"):
        st.session_state["current_menu"] = "chats"
        st.rerun()

elif st.session_state.get("current_menu") == "search":
    st.header("🔍 Найти людей")
    search_query = st.text_input("Введите логин", placeholder="Поиск...")
    
    if search_query:
        all_users = load_users()
        found = [u for u in all_users.keys() if search_query.lower() in u.lower() and u != curr]
        
        if found:
            for user in found:
                col1, col2 = st.columns([3, 1])
                with col1:
                    is_online = is_user_online(user)
                    status_dot = "🟢" if is_online else "⚪"
                    st.write(f"{status_dot} 🕊️ **{user}**")
                with col2:
                    contacts = load_contacts(curr)
                    if user in contacts:
                        st.success("✓ В друзьях")
                    elif is_friend_request_sent(curr, user):
                        st.info("⏳ Заявка отправлена")
                    else:
                        if st.button("➕", key=f"add_{user}"):
                            send_friend_request(curr, user)
                            st.rerun()
        else:
            st.caption("Никого не найдено")
    
    if st.button("← Назад"):
        st.session_state["current_menu"] = "chats"
        st.rerun()

else:
    # --- ГЛАВНЫЙ ЭКРАН (ЧАТ) ---
    curr = st.session_state["logged_user"]
    target = st.session_state.get("selected_chat")
    chat_type = st.session_state.get("chat_type", "private")
    
    if target:
        # Проверяем новые сообщения из WebSocket
        if "new_ws_message" in st.session_state and st.session_state["new_ws_message"]:
            try:
                new_msg = json.loads(st.session_state["new_ws_message"])
                if new_msg.get("target") == curr or new_msg.get("chat_type") == "group":
                    save_message(
                        new_msg["sender"],
                        new_msg["target"],
                        new_msg["text"],
                        new_msg.get("type", "text"),
                        new_msg.get("chat_type", "private")
                    )
            except:
                pass
            st.session_state["new_ws_message"] = None
        
        col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
        with col1:
            icon = "👥" if chat_type == "group" else "💬"
            
            if chat_type == "private":
                is_online = is_user_online(target)
                status_dot = '<span class="online-dot"></span>' if is_online else '<span class="offline-dot"></span>'
                last_seen = get_user_last_seen(target)
                status_text = "онлайн" if is_online else f"был {format_last_seen(last_seen)}"
                st.markdown(f"{status_dot} {icon} **{target}** — *{status_text}*", unsafe_allow_html=True)
            else:
                st.header(f"{icon} {target}")
        
        with col2:
            if WEBRTC_AVAILABLE:
                with st.expander("🎙️", expanded=False):
                    webrtc_streamer(
                        key=f"voice-{target}",
                        mode=WebRtcMode.SENDRECV,
                        rtc_configuration=RTCConfiguration(
                            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
                        ),
                        media_stream_constraints={"video": False, "audio": True},
                    )
        
        with col3:
            if st.button("😊", help="Стикеры"):
                st.session_state["show_stickers"] = not st.session_state.get("show_stickers", False)
        
        with col4:
            if st.button("✖️", help="Закрыть чат"):
                st.session_state["selected_chat"] = None
                st.rerun()
        
        st.divider()
        
        # Стикеры
        if st.session_state.get("show_stickers", False):
            st.write("**Стикеры:**")
            sticker_cols = st.columns(8)
            stickers = ["👍", "❤️", "😂", "😮", "😢", "😡", "🎉", "🕊️"]
            
            for i, sticker in enumerate(stickers):
                with sticker_cols[i]:
                    if st.button(sticker, key=f"sticker_{sticker}_{target}"):
                        save_message(curr, target, sticker, "text", chat_type)
                        st.session_state["show_stickers"] = False
                        st.rerun()
            st.divider()
        
        # Статус "печатает..."
        if chat_type == "private" and is_user_typing(target, curr):
            st.markdown(f"""
            <div class="typing-indicator">
                {target} печатает<span class="typing-dots"></span>
            </div>
            """, unsafe_allow_html=True)
        
        # История сообщений
        chat_container = st.container()
        
        with chat_container:
            msgs = load_messages()
            
            if chat_type == "private":
                chat_msgs = [m for m in msgs if (m["sender"] == curr and m["target"] == target) or 
                            (m["sender"] == target and m["target"] == curr)]
            else:
                chat_msgs = [m for m in msgs if m.get("target") == target and m.get("chat_type") == "group"]
            
            if not chat_msgs:
                st.info(f"💬 Начните общение! Отправьте первое сообщение.")
            else:
                for m in chat_msgs:
                    is_me = m["sender"] == curr
                    align = "flex-end" if is_me else "flex-start"
                    bg = "#DCF8C6" if is_me else "#FFFFFF"
                    
                    if m.get("type") == "photo":
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.image(m["photo_path"], caption=f"{m['sender']} - {m['time']}", width=300)
                    else:
                        st.markdown(f"""
                        <div style="display: flex; justify-content: {align}; margin: 5px 0;">
                            <div class="message-bubble" style="background: {bg}; padding: 10px; border-radius: 15px; max-width: 70%; 
                                        border: 1px solid #ccc; color: #000000;
                                        animation: fadeIn 0.3s ease-in;">
                                <b style="color: #000000;">{m['sender']}</b><br>
                                <span style="color: #000000;">{m['text']}</span><br>
                                <small style="color: #666666;">{m['time']}</small>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Отправка
        col1, col2 = st.columns([5, 1])
        
        with col1:
            text = st.chat_input(f"Написать в {target}...", key=f"chat_input_{target}")
            if text:
                update_typing_status(curr, target, False)
        
        with col2:
            uploaded_photo = st.file_uploader("📷", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed", key=f"photo_{target}")
        
        if st.session_state.get(f"chat_input_{target}"):
            update_typing_status(curr, target, True)
        
        if text:
            save_message(curr, target, text, "text", chat_type)
            st.rerun()
        
        if uploaded_photo:
            save_photo(curr, target, uploaded_photo.getvalue(), chat_type)
            st.rerun()
    
    else:
        st.markdown("<center><h1>🕊️ Pigeon Messenger</h1></center>", unsafe_allow_html=True)
        st.markdown("<center><p>Мессенджер для своих • Звонки • Чаты • Фото</p></center>", unsafe_allow_html=True)
        
        st.divider()
        
        contacts = load_contacts(curr)
        groups = get_user_groups(curr)
        
        if contacts or groups:
            st.subheader("📋 Последние чаты")
            
            for contact in contacts:
                last_msg = get_last_message(curr, contact, "private")
                is_online = is_user_online(contact)
                status_dot = '<span class="online-dot"></span>' if is_online else '<span class="offline-dot"></span>'
                
                col1, col2, col3 = st.columns([1, 5, 1])
                with col1:
                    st.markdown(status_dot, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{contact}**<br><small>{last_msg}</small>", unsafe_allow_html=True)
                with col3:
                    if st.button("💬", key=f"open_{contact}"):
                        st.session_state["selected_chat"] = contact
                        st.session_state["chat_type"] = "private"
                        st.rerun()
                st.divider()
            
            for group in groups:
                last_msg = get_last_message(curr, group, "group")
                
                col1, col2, col3 = st.columns([1, 5, 1])
                with col1:
                    st.markdown("👥")
                with col2:
                    st.markdown(f"**{group}**<br><small>{last_msg}</small>", unsafe_allow_html=True)
                with col3:
                    if st.button("💬", key=f"open_grp_{group}"):
                        st.session_state["selected_chat"] = group
                        st.session_state["chat_type"] = "group"
                        st.rerun()
                st.divider()
        else:
            st.info("👋 Добро пожаловать! Нажмите 🔍 в боковом меню, чтобы найти друзей!")
