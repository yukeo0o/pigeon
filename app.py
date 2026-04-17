import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import os

# ПРЯМАЯ ССЫЛКА НА ТВОЮ ТАБЛИЦУ (БЕЗ SECRETS)
URL = "https://google.com"

st.set_page_config(page_title="Pigeon 2.4", page_icon="🕊️", layout="wide")

# Подключение (теперь напрямую)
conn = st.connection("gsheets", type=GSheetsConnection)

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
            st.session_state["logged_user"] = u_in
            st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🕊️")
        
        st.write("---")
        st.write("### Начни общаться 💬")
        search = st.text_input("", placeholder="Поиск друзей...", label_visibility="collapsed").strip().lower()
        
        try:
            # ЧИТАЕМ НАПРЯМУЮ ПО URL
            user_df = conn.read(spreadsheet=URL, worksheet="0", ttl=0)
            all_users = user_df["username"].astype(str).tolist()
            
            if search:
                found = [u for u in all_users if search in u.lower() and u != curr]
                if found:
                    for f in found:
                        if st.button(f"👤 {f}", use_container_width=True):
                            st.session_state["selected_chat"] = f
                            st.rerun()
                else:
                    st.caption("Голубь не найден... 🕊️")
        except Exception as e:
            st.error("База пока не проснулась...")

        if st.button("Выйти", type="primary"):
            st.session_state["logged_user"] = None
            st.rerun()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    if target:
        st.header(f"Чат с {target}")
        st.divider()
        st.chat_input(f"Напиши {target}...")
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга в поиске слева</h3></center>", unsafe_allow_html=True)
