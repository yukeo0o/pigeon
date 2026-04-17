import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import extra_streamlit_components as stx
import time
import pandas as pd
import base64
from PIL import Image
import io
import hashlib
import secrets
from streamlit_autorefresh import st_autorefresh

# Автообновление каждые 2 секунды (для real-time чата)
st_autorefresh(interval=2000, limit=100000, debounce=True)

# Проверяем, установлен ли streamlit-webrtc
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# Файлы
MESSAGES_FILE = Path("messages/messages.json")
USERS_FILE = Path("users/users.json")
CONTACTS_FILE = Path("users/contacts.json")
GROUPS_FILE = Path("users/groups.json")
INVITES_FILE = Path("users/invites.json")

# Создаем папки
Path("messages").mkdir(exist_ok=True)
Path("users").mkdir(exist_ok=True)
Path("messages/photos").mkdir(parents=True, exist_ok=True)

# Куки
cookie_manager = stx.CookieManager()
time.sleep(0.5)

if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = cookie_manager.get(cookie="pigeon_user_v7")

if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

if "chat_type" not in st.session_state:
    st.session_state["chat_type"] = "private"

# --- ФУНКЦИИ БЕЗОПАСНОСТИ ---
def hash_password(password):
    """Хеширует пароль"""
    salt = "pigeon_salt_2024"  # В реальном проекте используй случайную соль
    return hashlib.sha256((password + salt).encode()).hexdigest()

def check_password(username, password):
    """Проверяет пароль пользователя"""
    users = load_users()
    if username in users:
        return users[username].get("password") == hash_password(password)
    return False

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
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
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now().isoformat()
    })
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(msgs, f, ensure_ascii=False)

def save_photo(sender, target, photo_bytes, chat_type="private"):
    photo_dir = Path("messages/photos")
    photo_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{sender}.jpg"
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
        "time": datetime.now().strftime("%H:%M"),
        "timestamp": datetime.now().isoformat()
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
            "created": datetime.now().isoformat(),
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
        "created": datetime.now().isoformat()
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

def load_invites():
    if INVITES_FILE.exists():
        with open(INVITES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def create_invite_code():
    import random
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

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
                        cookie_manager.set("pigeon_user_v7", login_name, expires_at=datetime.now() + pd.Timedelta(days=30))
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
                        cookie_manager.set("pigeon_user_v7", reg_name, expires_at=datetime.now() + pd.Timedelta(days=30))
                        st.success("Регистрация успешна!")
                        st.rerun()
        
        st.divider()
        st.caption(f"👥 Пользователей: {len(load_users())}")
    
    else:
        curr = st.session_state["logged_user"]
        
        st.markdown(f"### 🕊️ {curr}")
        
        menu = st.radio("", ["💬 Чаты", "👥 Группы", "👤 Контакты", "🔍 Поиск", "⚙️ Профиль"], label_visibility="collapsed")
        
        st.divider()
        
        if menu == "💬 Чаты":
            st.subheader("Ваши чаты")
            
            contacts = load_contacts(curr)
            if contacts:
                for contact in contacts:
                    last_msg = get_last_message(curr, contact, "private")
                    
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        if st.button(f"💬 {contact}\n_{last_msg}_", key=f"chat_{contact}", use_container_width=True):
                            st.session_state["selected_chat"] = contact
                            st.session_state["chat_type"] = "private"
                            st.rerun()
                    with col2:
                        if st.button("❌", key=f"del_{contact}", help="Удалить из контактов"):
                            remove_contact(curr, contact)
                            st.rerun()
            
            groups = get_user_groups(curr)
            if groups:
                for group in groups:
                    last_msg = get_last_message(curr, group, "group")
                    
                    if st.button(f"👥 {group}\n_{last_msg}_", key=f"group_{group}", use_container_width=True):
                        st.session_state["selected_chat"] = group
                        st.session_state["chat_type"] = "group"
                        st.rerun()
            
            if not contacts and not groups:
                st.info("Нет чатов. Добавьте друзей или создайте группу!")
        
        elif menu == "👥 Группы":
            st.subheader("Групповые чаты")
            
            with st.expander("➕ Создать группу"):
                group_name = st.text_input("Название группы")
                all_users = list(load_users().keys())
                if curr in all_users:
                    all_users.remove(curr)
                selected_members = st.multiselect("Выберите участников", all_users)
                
                if st.button("Создать группу", use_container_width=True):
                    if group_name and selected_members:
                        members = [curr] + selected_members
                        save_group(group_name, curr, members)
                        st.success(f"Группа '{group_name}' создана!")
                        st.rerun()
            
            groups = get_user_groups(curr)
            if groups:
                st.subheader("Мои группы")
                for group in groups:
                    group_data = load_groups().get(group, {})
                    members = group_data.get("members", [])
                    
                    with st.expander(f"👥 {group} ({len(members)} участников)"):
                        st.write("**Участники:**")
                        for member in members:
                            st.write(f"🕊️ {member}")
                        
                        if st.button(f"💬 Открыть чат", key=f"open_group_{group}"):
                            st.session_state["selected_chat"] = group
                            st.session_state["chat_type"] = "group"
                            st.rerun()
        
        elif menu == "👤 Контакты":
            st.subheader("Мои контакты")
            contacts = load_contacts(curr)
            if contacts:
                for contact in contacts:
                    st.write(f"🕊️ {contact}")
            else:
                st.info("Список контактов пуст")
        
        elif menu == "🔍 Поиск":
            st.subheader("🔍 Найти людей")
            search = st.text_input("Введите логин", placeholder="Поиск...")
            
            if search:
                all_users = load_users()
                found = [u for u in all_users.keys() if search.lower() in u.lower() and u != curr]
                
                if found:
                    for user in found:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"🕊️ **{user}**")
                        with col2:
                            contacts = load_contacts(curr)
                            if user in contacts:
                                st.success("✓ В контактах")
                            else:
                                if st.button("➕", key=f"add_{user}", help="Добавить в контакты"):
                                    save_contact(curr, user)
                                    st.rerun()
                else:
                    st.caption("Никого не найдено")
        
        elif menu == "⚙️ Профиль":
            st.subheader("Мой профиль")
            users = load_users()
            user_data = users.get(curr, {})
            
            st.write(f"**Логин:** {curr}")
            st.write(f"**Дата регистрации:** {user_data.get('created', 'Неизвестно')[:10]}")
            
            # Статистика
            st.divider()
            msgs = load_messages()
            sent = len([m for m in msgs if m["sender"] == curr])
            received = len([m for m in msgs if m.get("target") == curr])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📤 Отправлено", sent)
            with col2:
                st.metric("📥 Получено", received)
        
        st.divider()
        
        if st.button("🚪 Выйти", use_container_width=True):
            cookie_manager.delete("pigeon_user_v7")
            st.session_state["logged_user"] = None
            st.session_state["selected_chat"] = None
            st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    curr = st.session_state["logged_user"]
    target = st.session_state.get("selected_chat")
    chat_type = st.session_state.get("chat_type", "private")
    
    if target:
        col1, col2, col3, col4 = st.columns([5, 1, 1, 1])
        with col1:
            icon = "👥" if chat_type == "group" else "💬"
            st.header(f"{icon} {target}")
        
        with col2:
            if WEBRTC_AVAILABLE:
                with st.expander("🎙️ Звонок", expanded=False):
                    webrtc_streamer(
                        key=f"voice-{target}",
                        mode=WebRtcMode.SENDRECV,
                        rtc_configuration=RTCConfiguration(
                            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
                        ),
                        media_stream_constraints={"video": False, "audio": True},
                    )
            else:
                if st.button("🎙️", help="Установите: pip install streamlit-webrtc"):
                    st.toast("pip install streamlit-webrtc")
        
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
                            <div style="background: {bg}; padding: 10px; border-radius: 15px; max-width: 70%; 
                                        border: 1px solid #ddd;">
                                <b>{m['sender']}</b><br>
                                {m['text']}<br>
                                <small style="color: #666;">{m['time']}</small>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        
        st.divider()
        
        # Отправка
        col1, col2 = st.columns([5, 1])
        
        with col1:
            text = st.chat_input(f"Написать в {target}...")
        
        with col2:
            uploaded_photo = st.file_uploader("📷", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed", key=f"photo_{target}")
        
        if text:
            save_message(curr, target, text, "text", chat_type)
            st.rerun()
        
        if uploaded_photo:
            save_photo(curr, target, uploaded_photo.getvalue(), chat_type)
            st.rerun()
    
    else:
        st.markdown("<center><h1>🕊️ Pigeon Messenger</h1></center>", unsafe_allow_html=True)
        st.markdown("<center><p>Семейный мессенджер • Звонки • Чаты • Фото</p></center>", unsafe_allow_html=True)
        
        st.divider()
        
        contacts = load_contacts(curr)
        groups = get_user_groups(curr)
        
        if contacts or groups:
            st.subheader("📋 Последние чаты")
            
            for contact in contacts:
                last_msg = get_last_message(curr, contact, "private")
                
                col1, col2, col3 = st.columns([1, 5, 1])
                with col1:
                    st.markdown("💬")
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
                    if st.button("💬", key=f"open_group_main_{group}"):
                        st.session_state["selected_chat"] = group
                        st.session_state["chat_type"] = "group"
                        st.rerun()
                st.divider()
        else:
            st.info("👋 Добро пожаловать! Перейдите в 'Поиск' или 'Группы' в боковом меню, чтобы начать общение!")
