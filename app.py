import streamlit as st
import os
import json
from datetime import datetime

st.set_page_config(page_title="Pigeon Messenger", page_icon="🐦", layout="wide")

# Создаем папки
for folder in ["users", "avatars", "messages"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- МАГИЯ ВЕЧНОГО ВХОДА ---
SESSION_FILE = "last_session.txt"

if "logged_user" not in st.session_state:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            st.session_state["logged_user"] = f.read().strip()
    else:
        st.session_state["logged_user"] = None

if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

# Функции для управления сессией
def login(username):
    st.session_state["logged_user"] = username
    with open(SESSION_FILE, "w") as f:
        f.write(username)

def logout():
    st.session_state["logged_user"] = None
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)
    st.rerun()

# Функции для работы с данными
def save_user(username, data):
    with open(f"users/{username}.json", "w", encoding="utf-8") as f:
        json.dump(data, f)

def get_user(username):
    path = f"users/{username}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("Вход в Pigeon")
        mode = st.radio("Действие:", ["Логин", "Регистрация"])
        u_input = st.text_input("Никнейм").strip()
        
        if mode == "Регистрация":
            e_input = st.text_input("Почта")
            p_input = st.text_input("Пароль", type="password")
            avatar = st.file_uploader("Аватарка", type=['png', 'jpg'])
            if st.button("Создать аккаунт"):
                if u_input and p_input and "@" in e_input:
                    save_user(u_input, {"email": e_input, "password": p_input, "status": "В сети", "bio": "Я в Pigeon!"})
                    if avatar:
                        with open(f"avatars/{u_input}.png", "wb") as f:
                            f.write(avatar.getbuffer())
                    st.success("Аккаунт создан! Теперь войдите.")
        else:
            p_input = st.text_input("Пароль", type="password")
            if st.button("Войти"):
                user_data = get_user(u_input)
                if user_data and user_data["password"] == p_input:
                    login(u_input)
                    st.rerun()
                else:
                    st.error("Ошибка входа")
    else:
        # ИНТЕРФЕЙС АВТОРИЗОВАННОГО ПОЛЬЗОВАТЕЛЯ
        curr = st.session_state["logged_user"]
        u_data = get_user(curr)
        
        # 1. ПОИСК В САМОМ ВЕРХУ
        st.write("### Начни общаться 💬")
        search = st.text_input("", placeholder="Поиск друзей...", label_visibility="collapsed").strip().lower()
        
        # 2. СПИСОК ЧАТОВ
        friends = [f.replace(".json", "") for f in os.listdir("users") if f != curr]
        for f in friends:
            if search in f.lower():
                if st.button(f"👤 {f}", use_container_width=True, key=f"chat_{f}"):
                    st.session_state["selected_chat"] = f
                    st.rerun()
        
        st.divider()
        
        # 3. НАСТРОЙКИ ВНИЗУ
        with st.expander(f"⚙️ Настройки"):
            if os.path.exists(f"avatars/{curr}.png"):
                st.image(f"avatars/{curr}.png", width=80)
            st.write(f"**Ник:** {curr}")
            new_status = st.text_input("Статус", value=u_data.get("status", "В сети"))
            new_bio = st.text_area("О себе", value=u_data.get("bio", ""))
            
            if st.button("Сохранить"):
                u_data["status"] = new_status
                u_data["bio"] = new_bio
                save_user(curr, u_data)
                st.rerun()
            
            if st.button("Выйти", use_container_width=True, type="primary"):
                logout()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    target = st.session_state["selected_chat"]
    if target:
        # Карточка собеседника
        t_data = get_user(target)
        c1, c2 = st.columns([1, 10])
        with c1:
            if os.path.exists(f"avatars/{target}.png"):
                st.image(f"avatars/{target}.png", width=50)
        with c2:
            st.subheader(target)
            st.caption(f"{t_data.get('status', '')} | {t_data.get('bio', '')}")
        
        chat_id = "_".join(sorted([st.session_state["logged_user"], target]))
        path = f"messages/{chat_id}.txt"
        st.divider()
        
        # Окно сообщений
        container = st.container(height=500)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f.readlines():
                    container.write(line.strip())

        if prompt := st.chat_input(f"Написать {target}..."):
            time_now = datetime.now().strftime("%H:%M")
            new_entry = f"[{time_now}] **{st.session_state['logged_user']}**: {prompt}"
            with open(path, "a", encoding="utf-8") as f:
                f.write(new_entry + "\n")
            st.rerun()
    else:
        st.markdown("<br><br><br><center><h1>🐦 Pigeon</h1><h3>Выбери друга слева, чтобы начать</h3></center>", unsafe_allow_html=True)
else:
    st.title("🐦 Pigeon Messenger")
    st.info("Войди в систему через боковую панель.")
