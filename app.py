import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time

# --- НАСТРОЙКИ ---
URL = "https://google.com"

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# --- МЕНЕДЖЕР ПАМЯТИ (КУКИ) ---
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# Небольшая пауза, чтобы браузер успел передать данные
time.sleep(0.5)

if "logged_user" not in st.session_state:
    saved_user = cookie_manager.get(cookie="pigeon_user")
    st.session_state["logged_user"] = saved_user

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("Pigeon: Вход")
        u_in = st.text_input("Никнейм").strip()
        if st.button("Покурлыкаем? 🕊️"):
            if u_in:
                st.session_state["logged_user"] = u_in
                cookie_manager.set("pigeon_user", u_in, expires_at=datetime.now() + pd.Timedelta(days=30))
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🕊️")
        
        st.write("---")
        st.write("### Начни общаться")
        search = st.text_input("", placeholder="Поиск друга...", label_visibility="collapsed").strip().lower()
        
        try:
            # Читаем базу данных
            df = pd.read_csv(URL)
            all_users = df["username"].astype(str).tolist()
            
            if search:
                found = [u for u in all_users if search in u.lower() and u != curr]
                if found:
                    for f in found:
                        if st.button(f"👤 {f}", use_container_width=True):
                            st.session_state["selected_chat"] = f
                            st.rerun()
                else:
                    st.caption("Голубь не найден...")
        except:
            st.error("Ошибка связи с базой")

        st.write("---")
        if st.button("Улететь (Выход)", type="primary"):
            cookie_manager.delete("pigeon_user")
            st.session_state["logged_user"] = None
            st.session_state["selected_chat"] = None
            st.rerun()

# --- ЭКРАН ЧАТА ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    
    if target:
        st.subheader(f"Чат с {target}")
        
        # Кнопка медиа
        with st.expander("📎 Прикрепить медиа"):
            file = st.file_uploader("Выбери фото", type=['png', 'jpg', 'jpeg'])
            if file and st.button("Отправить фото"):
                st.session_state["chat_history"].append({"sender": st.session_state["logged_user"], "type": "img", "content": file})

        st.divider()
        
        # Отображение истории (локальной для текущей сессии)
        chat_container = st.container(height=400)
        for msg in st.session_state["chat_history"]:
            if msg["type"] == "text":
                chat_container.write(f"**{msg['sender']}**: {msg['content']}")
            else:
                chat_container.write(f"**{msg['sender']}** прислал фото:")
                chat_container.image(msg["content"], width=250)

        # Поле ввода
        if prompt := st.chat_input(f"Написать {target}..."):
            st.session_state["chat_history"].append({"sender": st.session_state["logged_user"], "type": "text", "content": prompt})
            st.rerun()
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга в поиске слева</h3></center>", unsafe_allow_html=True)

