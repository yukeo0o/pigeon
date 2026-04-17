import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time

# --- НАСТРОЙКИ (ТВОЙ ID ТАБЛИЦЫ) ---
URL = "https://google.com"

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# --- МЕНЕДЖЕР КУКИ (ВЕЧНАЯ ПАМЯТЬ) ---
# Создаем менеджер напрямую без кэширования
cookie_manager = stx.CookieManager()

# Обязательная пауза, иначе библиотека не успевает прочитать куки из браузера
time.sleep(0.5)

if "logged_user" not in st.session_state:
    # Проверяем, есть ли сохраненный ник в браузере
    saved_user = cookie_manager.get(cookie="pigeon_user_v1")
    st.session_state["logged_user"] = saved_user

if "selected_chat" not in st.session_state:
    st.session_state["selected_chat"] = None

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
                # Сохраняем ник в браузер на 30 дней
                cookie_manager.set("pigeon_user_v1", u_in, expires_at=datetime.now() + pd.Timedelta(days=30))
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🕊️")
        
        st.write("---")
        st.write("### Начни общаться")
        search = st.text_input("", placeholder="Поиск друга...", label_visibility="collapsed").strip().lower()
        
        try:
            # Читаем базу данных из Google
            df = pd.read_csv(URL)
            all_users = df["username"].astype(str).tolist()
            
            if search:
                found = [u for u in all_users if search in str(u).lower() and str(u) != curr]
                if found:
                    for f in found:
                        if st.button(f"👤 {f}", use_container_width=True, key=f"btn_{f}"):
                            st.session_state["selected_chat"] = f
                            st.rerun()
                else:
                    st.caption("Голубь не найден... 🕊️")
        except:
            st.error("База данных пока недоступна")

        st.write("---")
        if st.button("Улететь (Выход)", type="primary", use_container_width=True):
            cookie_manager.delete("pigeon_user_v1")
            st.session_state["logged_user"] = None
            st.session_state["selected_chat"] = None
            st.rerun()

# --- ЭКРАН ЧАТА ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    
    if target:
        st.subheader(f"Чат с {target}")
        
        # КНОПКА МЕДИА (СКРЕПКА) 📎
        with st.expander("📎 Прикрепить фото или стикер"):
            file = st.file_uploader("Выбери файл", type=['png', 'jpg', 'jpeg'])
            if file and st.button("Отправить медиа"):
                st.session_state["chat_history"].append({
                    "sender": st.session_state["logged_user"], 
                    "type": "img", 
                    "content": file,
                    "time": datetime.now().strftime("%H:%M")
                })

        st.divider()
        
        # Отображение сообщений
        chat_container = st.container(height=450)
        for msg in st.session_state["chat_history"]:
            t = msg.get("time", "")
            if msg["type"] == "text":
                chat_container.write(f"[{t}] **{msg['sender']}**: {msg['content']}")
            else:
                chat_container.write(f"[{t}] **{msg['sender']}** прислал фото:")
                chat_container.image(msg["content"], width=300)

        # Поле ввода
        if prompt := st.chat_input(f"Написать {target}..."):
            st.session_state["chat_history"].append({
                "sender": st.session_state["logged_user"], 
                "type": "text", 
                "content": prompt,
                "time": datetime.now().strftime("%H:%M")
            })
            st.rerun()
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга в поиске слева</h3></center>", unsafe_allow_html=True)
else:
    st.info("Пожалуйста, введите свой ник в боковой панели, чтобы покурлыкать.")
