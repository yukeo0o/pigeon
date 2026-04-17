import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time
import requests # Нужен для отправки формы

# --- НАСТРОЙКИ ---
# Ссылка на твою таблицу (для чтения сообщений)
URL_CSV = "https://google.com"
# Ссылка на отправку формы (твой "передатчик")
FORM_URL = "https://google.com"

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# --- ПАМЯТЬ ВХОДА ---
cookie_manager = stx.CookieManager()
time.sleep(0.5)

if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = cookie_manager.get(cookie="pigeon_user_v3")

# --- ФУНКЦИИ ---
def send_message(sender, target, text):
    # Те самые ID, которые я вытащил из твоей ссылки
    payload = {
        "entry.2062635904": sender, 
        "entry.1764614138": target, 
        "entry.362141529": text
    }
    try:
        requests.post(FORM_URL, data=payload)
        return True
    except:
        return False

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("Pigeon: Вход")
        u_in = st.text_input("Никнейм").strip()
        if st.button("Покурлыкаем? 🕊️"):
            if u_in:
                st.session_state["logged_user"] = u_in
                cookie_manager.set("pigeon_user_v3", u_in)
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🕊️")
        st.write("---")
        
        # ПОИСК
        search = st.text_input("Поиск друзей", placeholder="Ник...").strip().lower()
        try:
            df = pd.read_csv(URL_CSV)
            all_users = df["username"].astype(str).tolist()
            if search:
                found = [u for u in all_users if search in u.lower() and u != curr]
                for f in found:
                    if st.button(f"👤 {f}", use_container_width=True):
                        st.session_state["selected_chat"] = f
                        st.rerun()
        except:
            st.caption("База данных в пути...")

        if st.button("Выйти", type="primary"):
            cookie_manager.delete("pigeon_user_v3")
            st.session_state["logged_user"] = None
            st.rerun()

# --- ЧАТ ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    if target:
        st.header(f"Чат с {target}")
        
        # Загрузка и показ сообщений
        try:
            msgs_df = pd.read_csv(URL_CSV) # Читаем ту же таблицу (или лист с ответами)
            # Фильтруем сообщения только для этой пары
            chat_msgs = msgs_df[((msgs_df['sender'] == st.session_state["logged_user"]) & (msgs_df['target'] == target)) | 
                                ((msgs_df['sender'] == target) & (msgs_df['target'] == st.session_state["logged_user"]))]
            
            for index, row in chat_msgs.iterrows():
                st.write(f"**{row['sender']}**: {row['text']}")
        except:
            st.caption("Сообщений пока нет. Будь первым!")

        if prompt := st.chat_input(f"Написать {target}..."):
            if send_message(st.session_state["logged_user"], target, prompt):
                st.rerun()
            else:
                st.error("Ошибка отправки")
    else:
        st.markdown("<center><h1>🕊️ Pigeon</h1><h3>Найди друга в поиске</h3></center>", unsafe_allow_html=True)
