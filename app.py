import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx # Магия для памяти

# ССЫЛКА НА ТАБЛИЦУ
URL = "https://google.com"

st.set_page_config(page_title="Pigeon 2.5", page_icon="🕊️", layout="wide")

# --- ИНИЦИАЛИЗАЦИЯ КУКИ ---
cookie_manager = stx.CookieManager()

# Пытаемся достать ник из браузера
if "logged_user" not in st.session_state:
    saved_user = cookie_manager.get(cookie="pigeon_user_name")
    st.session_state["logged_user"] = saved_user

# --- ФУНКЦИИ ВХОДА ---
def login_user(username):
    st.session_state["logged_user"] = username
    # Запоминаем на 30 дней
    cookie_manager.set("pigeon_user_name", username, expires_at=datetime.now() + pd.Timedelta(days=30))

def logout_user():
    st.session_state["logged_user"] = None
    cookie_manager.delete("pigeon_user_name")
    st.rerun()

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    if st.session_state["logged_user"] is None:
        st.header("Pigeon: Вход")
        u_in = st.text_input("Никнейм").strip()
        if st.button("Покурлыкаем? 🕊️"):
            if u_in:
                login_user(u_in)
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🕊️")
        
        st.write("---")
        st.write("### Начни общаться 💬")
        
        try:
            user_df = pd.read_csv(URL)
            all_users = user_df["username"].astype(str).tolist()
        except:
            all_users = ["lipwix", "Yukeo"]

        search = st.text_input("Поиск", placeholder="Ник...", label_visibility="collapsed").strip().lower()

        if search:
            found = [u for u in all_users if search in str(u).lower() and str(u) != curr]
            if found:
                for f in found:
                    if st.button(f"👤 {f}", use_container_width=True):
                        st.session_state["selected_chat"] = f
                        st.rerun()
            else:
                st.caption("Голубь не найден... 🕊️")
        
        st.write("---")
        if st.button("Улететь (Выход)", type="primary"):
            logout_user()

# --- ГЛАВНЫЙ ЭКРАН ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    if target:
        st.header(f"Чат с {target}")
        
        with st.expander("📎 Прикрепить медиа"):
            file = st.file_uploader("Выбери фото", type=['png', 'jpg', 'jpeg'])
            if file and st.button("Отправить фото"):
                st.image(file, width=250)
                st.success("Доставлено! 📸")

        st.divider()
        if prompt := st.chat_input(f"Написать {target}..."):
            st.write(f"**{st.session_state['logged_user']}**: {prompt}")
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга слева</h3></center>", unsafe_allow_html=True)
