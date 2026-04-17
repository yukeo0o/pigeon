import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time
import json
from pathlib import Path
from streamlit_autorefresh import st_autorefresh

# --- НАСТРОЙКИ ---
st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# Файл для хранения сообщений
MESSAGES_FILE = Path("pigeon_messages.json")
USERS_FILE = Path("pigeon_users.json")

# Автообновление каждые 2 секунды (чтобы видеть новые сообщения)
st_autorefresh(interval=2000, limit=100000, debounce=True)

# --- РАБОТА С ДАННЫМИ ---
def load_messages():
    """Загружает все сообщения из JSON файла"""
    if MESSAGES_FILE.exists():
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_message(sender, target, text):
    """Сохраняет новое сообщение"""
    messages = load_messages()
    messages.append({
        "sender": sender,
        "target": target,
        "text": text,
        "time": datetime.now().strftime("%H:%M:%S"),
        "timestamp": datetime.now().isoformat()
    })
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
    return True

def load_users():
    """Загружает всех зарегистрированных пользователей"""
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user(username):
    """Регистрирует нового пользователя"""
    users = load_users()
    if username not in users:
        users[username] = {
            "created": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat()
        }
    else:
        users[username]["last_seen"] = datetime.now().isoformat()
    
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_all_users():
    """Возвращает список всех пользователей"""
    return list(load_users().keys())

def get_chat_history(user1, user2):
    """Возвращает историю чата между двумя пользователями"""
    messages = load_messages()
    chat = []
    for msg in messages:
        if (msg["sender"] == user1 and msg["target"] == user2) or \
           (msg["sender"] == user2 and msg["target"] == user1):
            chat.append(msg)
    return chat

# --- ПАМЯТЬ И КУКИ ---
cookie_manager = stx.CookieManager()
time.sleep(0.6)

if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = cookie_manager.get(cookie="pigeon_user_v4")

if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

# Обновляем время последней активности
if st.session_state["logged_user"]:
    save_user(st.session_state["logged_user"])

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("🕊️ Pigeon Messenger")
        st.write("---")
        st.subheader("Вход или регистрация")
        u_in = st.text_input("Твой никнейм", placeholder="Например: CoolPigeon42").strip()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Войти", use_container_width=True):
                if u_in:
                    if u_in in get_all_users():
                        st.session_state["logged_user"] = u_in
                        cookie_manager.set("pigeon_user_v4", u_in, expires_at=datetime.now() + pd.Timedelta(days=30))
                        save_user(u_in)
                        st.rerun()
                    else:
                        st.error("Пользователь не найден!")
                else:
                    st.warning("Введи никнейм!")
        
        with col2:
            if st.button("✨ Создать", use_container_width=True):
                if u_in:
                    if u_in not in get_all_users():
                        st.session_state["logged_user"] = u_in
                        cookie_manager.set("pigeon_user_v4", u_in, expires_at=datetime.now() + pd.Timedelta(days=30))
                        save_user(u_in)
                        st.rerun()
                    else:
                        st.error("Этот ник уже занят!")
                else:
                    st.warning("Введи никнейм!")
        
        st.divider()
        st.caption(f"🐦 Уже с нами: {len(get_all_users())} голубей")
    
    else:
        curr = st.session_state["logged_user"]
        
        # Профиль
        st.markdown(f"### 🕊️ {curr}")
        
        # Статистика
        users = get_all_users()
        online_count = len(users)
        st.caption(f"👥 {online_count} пользователей онлайн")
        
        st.divider()
        
        # Поиск пользователей
        st.subheader("🔍 Найти друга")
        search = st.text_input("", placeholder="Введи ник...", label_visibility="collapsed").strip().lower()
        
        all_users = [u for u in users if u != curr]
        
        if search:
            found = [u for u in all_users if search in u.lower()]
        else:
            found = all_users
        
        if found:
            st.write("**Контакты:**")
            for user in found[:10]:  # Показываем только первых 10
                # Проверяем есть ли непрочитанные сообщения
                chat = get_chat_history(curr, user)
                unread_count = len([m for m in chat if m["target"] == curr and m["sender"] == user])
                
                button_label = f"💬 {user}"
                if unread_count > 0:
                    button_label = f"🔴 {user} ({unread_count})"
                
                if st.button(button_label, key=f"user_{user}", use_container_width=True):
                    st.session_state["selected_chat"] = user
                    st.rerun()
        else:
            st.caption("😢 Пока никого нет. Пригласи друзей!")
        
        st.divider()
        
        # Меню
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Обновить", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🚪 Выйти", use_container_width=True):
                cookie_manager.delete("pigeon_user_v4")
                st.session_state["logged_user"] = None
                st.session_state["selected_chat"] = None
                st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    curr = st.session_state["logged_user"]
    target = st.session_state.get("selected_chat")
    
    if target:
        # Шапка чата
        col1, col2 = st.columns([6, 1])
        with col1:
            st.header(f"💬 Чат с {target}")
        with col2:
            if st.button("✖️ Закрыть", use_container_width=True):
                st.session_state["selected_chat"] = None
                st.rerun()
        
        st.divider()
        
        # Контейнер для сообщений
        chat_container = st.container()
        
        with chat_container:
            chat_history = get_chat_history(curr, target)
            
            if not chat_history:
                st.info(f"✨ Начните общение с {target}! Отправьте первое сообщение.")
            else:
                for msg in chat_history:
                    is_sender = msg["sender"] == curr
                    align = "right" if is_sender else "left"
                    bg_color = "#DCF8C6" if is_sender else "#E8E8E8"
                    
                    with st.container():
                        cols = st.columns([1, 4, 1])
                        with cols[1 if not is_sender else 0]:
                            pass
                        with cols[1]:
                            st.markdown(f"""
                            <div style="
                                background-color: {bg_color};
                                padding: 10px;
                                border-radius: 10px;
                                margin: 5px 0;
                                text-align: {align};
                            ">
                                <b>{msg['sender']}</b><br>
                                {msg['text']}<br>
                                <small style="color: #666;">{msg['time']}</small>
                            </div>
                            """, unsafe_allow_html=True)
        
        # Поле ввода
        st.divider()
        col1, col2 = st.columns([5, 1])
        
        with col1:
            message_text = st.chat_input(f"Написать {target}...")
        
        # Отправка сообщения
        if message_text:
            save_message(curr, target, message_text)
            st.rerun()
    
    else:
        # Приветственный экран
        st.markdown("""
        <br><br>
        <center>
            <h1>🕊️ Добро пожаловать в Pigeon!</h1>
            <h3>Выбери друга слева и начни общение</h3>
            <br>
            <p style="color: #666;">
                ✨ Сообщения доставляются мгновенно<br>
                🔒 Все данные хранятся локально<br>
                🎯 Никакой рекламы и слежки
            </p>
        </center>
        """, unsafe_allow_html=True)
        
        # Показываем статистику
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Пользователей", len(get_all_users()))
        with col2:
            st.metric("💬 Сообщений", len(load_messages()))
        with col3:
            my_messages = len([m for m in load_messages() if m["sender"] == curr or m["target"] == curr])
            st.metric("📨 Мои сообщения", my_messages)

else:
    # Экран входа
    st.markdown("""
    <br><br><br>
    <center>
        <h1>🕊️ Pigeon Messenger</h1>
        <h3>Простой и быстрый мессенджер</h3>
        <br>
        <p style="color: #666; max-width: 500px; margin: 0 auto;">
            Войди или создай аккаунт в боковом меню слева.<br>
            Твои сообщения хранятся локально и доступны только тебе и собеседнику.
        </p>
        <br>
        <h4>🚀 Начни общаться прямо сейчас!</h4>
    </center>
    """, unsafe_allow_html=True)
    
    # Демо-статистика
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Всего пользователей", len(get_all_users()))
    with col2:
        st.metric("💬 Всего сообщений", len(load_messages()))
    with col3:
        st.metric("🕊️ Голубей онлайн", len(get_all_users()))
