import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ССЫЛКА НА ТАБЛИЦУ
URL = "https://google.com"

st.set_page_config(page_title="Pigeon 2.4", page_icon="🕊️", layout="wide")

# --- ПАМЯТЬ ВХОДА ---
if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = None
if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("Pigeon: Вход")
        u_in = st.text_input("Никнейм").strip()
        if st.button("Покурлыкаем? 🕊️"):
            if u_in:
                st.session_state["logged_user"] = u_in
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! Покурлыкаем? 🕊️")
        st.write("---")
        
        # --- ВОТ ОН, ЖИВОЙ ПОИСК (ИСПРАВЛЕННЫЙ) ---
        st.write("### Начни общаться 💬")
        try:
            # Превращаем ссылку для чтения через Pandas
            csv_url = URL.replace('/edit#gid=', '/export?format=csv&gid=')
            user_df = pd.read_csv(csv_url)
            all_users = user_df["username"].astype(str).tolist()
            
            search = st.text_input("", placeholder="Поиск друзей...", label_visibility="collapsed").strip().lower()

            if search:
                found = [u for u in all_users if search in str(u).lower() and str(u) != curr]
                if found:
                    for f in found:
                        if st.button(f"👤 {f}", use_container_width=True):
                            st.session_state["selected_chat"] = f
                            st.rerun()
                else:
                    st.caption("Голубь не найден... 🕊️")
        except Exception as e:
            st.error("База данных пока недоступна")
        
        st.write("---")
        if st.button("Выйти", type="primary"):
            st.session_state["logged_user"] = None
            st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    if target:
        st.header(f"Чат с {target}")
        
        # СКРЕПКА (МЕДИА) 📎
        with st.expander("📎 Прикрепить медиа"):
            file = st.file_uploader("Выбери фото", type=['png', 'jpg', 'jpeg'])
            if file:
                st.image(file, width=250)
                if st.button("Отправить в чат"):
                    st.success("Фото отправлено! 📸")

        st.divider()
        chat_box = st.container(height=400)
        
        if prompt := st.chat_input(f"Написать {target}..."):
            time = datetime.now().strftime("%H:%M")
            chat_box.write(f"**{st.session_state['logged_user']}** [{time}]: {prompt}")
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга в поиске слева</h3></center>", unsafe_allow_html=True)
