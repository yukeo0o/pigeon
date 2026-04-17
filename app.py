import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os

# 1. НАСТРОЙКИ (ТВОЙ ID ТАБЛИЦЫ)
URL = "https://google.com"

st.set_page_config(page_title="Pigeon 2.1", page_icon="🐦", layout="wide")

# Подключение к Google Таблице
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ЛОГИКА ВХОДА ---
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = None
if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("Pigeon: Вход")
        mode = st.radio("Действие", ["Логин", "Регистрация"])
        u_in = st.text_input("Никнейм").strip()
        p_in = st.text_input("Пароль", type="password")
        
        if mode == "Регистрация":
            e_in = st.text_input("Почта")
            if st.button("Создать аккаунт"):
                if u_in and p_in and "@" in e_in:
                    # Временно входим (полная запись в таблицу будет в след. шаге)
                    st.session_state["logged_user"] = u_in
                    st.rerun()
        else:
            if st.button("Войти"):
                st.session_state["logged_user"] = u_in
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🐦")
        
        # --- ЖИВОЙ ПОИСК (ТО, ЧТО МЫ ОБСУЖДАЛИ) ---
        st.write("---")
        st.write("### Начни общаться 💬")
        search = st.text_input("", placeholder="Поиск друзей...", label_visibility="collapsed").strip().lower()
        
        try:
            user_df = conn.read(spreadsheet=URL, worksheet="0")
            all_users = user_df["username"].astype(str).tolist()
        except:
            all_users = []

        if search:
            found = [u for u in all_users if search in u.lower() and u != curr]
            if found:
                for f in found:
                    if st.button(f"👤 {f}", use_container_width=True):
                        st.session_state["selected_chat"] = f
                        st.rerun()
            else:
                st.caption("Голубь не найден... 🐦")
        else:
            st.caption("Введите ник друга для поиска")

        st.write("---")
        if st.button("Выйти", type="primary"):
            st.session_state["logged_user"] = None
            st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    target = st.session_state["selected_chat"]
    if target:
        st.header(f"Чат с {target}")
        
        # КНОПКА МЕДИА (СКРЕПКА) 📎
        with st.expander("📎 Прикрепить фото или стикер"):
            file = st.file_uploader("Выбери файл", type=['png', 'jpg', 'jpeg'])
            if file:
                st.image(file, width=250)
                if st.button("Отправить медиа"):
                    st.success("Медиа отправлено!")

        st.divider()
        container = st.container(height=450)
        
        # Поле ввода
        if prompt := st.chat_input(f"Написать {target}..."):
            time = datetime.now().strftime("%H:%M")
            container.write(f"**{st.session_state['logged_user']}** [{time}]: {prompt}")
    else:
        st.markdown("<br><br><center><h1>🐦 Pigeon 2.1</h1><p>Найди друга в поиске слева</p></center>", unsafe_allow_html=True)
