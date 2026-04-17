import streamlit as st
import pandas as pd
from datetime import datetime
import extra_streamlit_components as stx
import time
import requests

# --- НАСТРОЙКИ (ПРЯМАЯ ССЫЛКА) ---
# Если эта ссылка верная, то после обновления кода всё заработает!
PIGEON_URL = "https://docs.google.com/spreadsheets/d/1kUNW0Zt4c85M69Cxcsp4SZ2TJ-KoahHjLMxuyXxDgII/edit?gid=0#gid=0"
FORM_URL = "https://google.com"

st.set_page_config(page_title="Pigeon Messenger", page_icon="🕊️", layout="wide")

# --- ПАМЯТЬ ---
cookie_manager = stx.CookieManager()
time.sleep(0.6)

if "logged_user" not in st.session_state:
    st.session_state["logged_user"] = cookie_manager.get(cookie="pigeon_user_v3")

# --- ОТПРАВКА ---
def send_msg(sender, target, text):
    payload = {"entry.2062635904": sender, "entry.1764614138": target, "entry.362141529": text}
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
                cookie_manager.set("pigeon_user_v3", u_in, expires_at=datetime.now() + pd.Timedelta(days=30))
                st.rerun()
    else:
        curr = st.session_state["logged_user"]
        st.write(f"### Привет, {curr}! 🕊️")
        st.write("---")
        st.write("### Начни общаться 💬")
        search = st.text_input("", placeholder="Поиск друга...", label_visibility="collapsed").strip().lower()
        
        try:
            # ЧИТАЕМ НАПРЯМУЮ, ИГНОРИРУЯ ВСЕ SECRETS
            df = pd.read_csv(PIGEON_URL)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'username' in df.columns:
                all_u = df["username"].astype(str).tolist()
                if search:
                    found = [u for u in all_u if search in str(u).lower() and str(u).strip() != curr]
                    if found:
                        for f in found:
                            if st.button(f"👤 {f}", use_container_width=True, key=f"u_{f}"):
                                st.session_state["selected_chat"] = f
                                st.rerun()
                    else:
                        st.caption("Голубь не найден... 🕊️")
                else:
                    st.caption("Введите ник")
            else:
                st.error("Колонка 'username' не найдена в таблице")
        except Exception as e:
            st.error("База данных временно недоступна")

        st.write("---")
        if st.button("Выход", type="primary", use_container_width=True):
            cookie_manager.delete("pigeon_user_v3")
            st.session_state["logged_user"] = None
            st.rerun()

# --- ЭКРАН ЧАТА ---
if st.session_state["logged_user"]:
    target = st.session_state.get("selected_chat")
    if target:
        st.header(f"Чат с {target}")
        st.divider()
        if prompt := st.chat_input(f"Написать {target}..."):
            if send_msg(st.session_state["logged_user"], target, prompt):
                st.toast("Отправлено! 🕊️")
                st.write(f"**Вы**: {prompt}")
    else:
        st.markdown("<br><br><center><h1>🕊️ Pigeon</h1><h3>Найди друга слева</h3></center>", unsafe_allow_html=True)
