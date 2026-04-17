import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time
import requests

# --- НАСТРОЙКИ (ТВОИ ССЫЛКИ) ---
# Ссылка на таблицу (Лист 1, где лежат ники)
URL_CSV = "https://google.com"
# Ссылка для отправки через твою форму
FORM_URL = "https://google.com"

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# --- ВЕЧНАЯ ПАМЯТЬ (КУКИ) ---
cookie_manager = stx.CookieManager()
time.sleep(0.5) # Пауза для прогрузки куки

if "logged_user" not in st.session_state:
    saved_user = cookie_manager.get(cookie="pigeon_user_v3")
    st.session_state["logged_user"] = saved_user

# --- ФУНКЦИЯ ОТПРАВКИ СООБЩЕНИЯ ---
def send_to_google(sender, target, text):
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
        
        # ЖИВОЙ ПОИСК
        st.write("### Начни общаться 💬")
        search = st.text_input("", placeholder="Поиск друга...", label_visibility="collapsed").strip().lower()
        
        try:
            df = pd.read_csv(URL_CSV)
            if 'username' in df.columns:
                all_users = df["username"].astype(str).tolist()
                if search:
                    found = [u for u in all_users if search in u.lower() and u != curr]
                    if found:
                        for f in found:
                            if st.button(f"👤 {f}", use_container_width=True):
                                st.session_state["selected_chat"] = f
                                st.rerun()
                    else:
                        st.caption("Голубь не найден... 🕊️")
                else:
                    st.caption("Введите ник для поиска")
            else:
                st.error("В таблице нет колонки 'username'!")
        except Exception as e:
            st.error("База данных временно недоступна")

        st.write("---")
        if st.button("Улететь (Выход)", type="primary", use_container_width=True):
            cookie_manager.delete("pigeon_user_v3")
            st.session_state["logged_user"] = None
            st.session_state["selected_chat"] = None
            st.rerun()

# --- ОСНОВНОЙ ЭКРАН ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    if target:
        st.header(f"Чат с {target}")
        st.divider()
        
        # Поле ввода и отправка
        if prompt := st.chat_input(f"Написать {target}..."):
            if send_to_google(st.session_state["logged_user"], target, prompt):
                st.toast("Курлык! Отправлено 🕊️")
                # Тут можно добавить логику показа сообщения, но для начала проверим отправку
                st.write(f"**Вы**: {prompt}")
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга в поиске слева</h3></center>", unsafe_allow_html=True)
