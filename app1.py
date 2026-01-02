import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import urllib.parse

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(page_title="Бетон Завод", layout="wide")

DB = "database.db"

USERS = {
    "director": {"password": "1234", "role": "director"},
    "buh": {"password": "1111", "role": "accountant"},
    "oper": {"password": "2222", "role": "operator"},
}

DRIVERS = [
    "Иванов", "Соколов", "Андреев",
    "Петров", "Кузнецов", "Морозов"
]

# ======================================================
# DATABASE
# ======================================================
conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS shipments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dt TEXT,
    tm TEXT,
    object TEXT,
    grade TEXT,
    driver TEXT,
    volume REAL,
    price_m3 REAL,
    total REAL,
    paid REAL,
    debt REAL,
    invoice TEXT,
    msg TEXT
)
""")
conn.commit()

# ======================================================
# AUTO LOGIN (через query params)
# ======================================================
params = st.experimental_get_query_params()

if "auth" not in st.session_state:
    if "user" in params and params["user"][0] in USERS:
        st.session_state.auth = True
        st.session_state.user = params["user"][0]
        st.session_state.role = USERS[params["user"][0]]["role"]
    else:
        st.session_state.auth = False

# ======================================================
# LOGIN
# ======================================================
if not st.session_state.auth:
    st.title("🔐 Вход")

    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")

    if st.button("Войти"):
        if u in USERS and USERS[u]["password"] == p:
            st.experimental_set_query_params(user=u)
            st.session_state.auth = True
            st.session_state.user = u
            st.session_state.role = USERS[u]["role"]
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

# ======================================================
# UI
# ======================================================
st.title("🏗 Управление отгрузкой бетона")
st.caption(f"Пользователь: {st.session_state.user} | Роль: {st.session_state.role}")

tabs = st.tabs(["📝 Отгрузка", "📊 Отчёты", "📈 Графики", "🚛 Водители"])

# ======================================================
# 📝 ОТГРУЗКА
# ======================================================
with tabs[0]:
    st.subheader("Формирование заявки")

    obj = st.text_input("📍 Объект")
    grade = st.selectbox("💎 Марка", ["М200","М250","М300","М350","М400"])
    selected = st.multiselect("🚛 Водители", DRIVERS)

    entries = []
    report = f"🏗 *ОТГРУЗКА БЕТОНА*\n📍 *Объект:* {obj}\n💎 *Марка:* {grade}\n────────────\n"

    for d in selected:
        c1, c2, c3, c4, c5 = st.columns([2,1,1,1,1])
        with c1:
            st.markdown(f"**{d}**")
        with c2:
            vol = st.number_input("м³", 0.0, step=0.5, key=f"v{d}")
        with c3:
            price = st.number_input("₸/м³", 0.0, step=100.0, key=f"p{d}")
        with c4:
            paid = st.number_input("Оплачено ₸", 0.0, step=1000.0, key=f"pay{d}")
        with c5:
            inv = st.text_input("Накл.", key=f"n{d}")

        if vol > 0 and price > 0:
            total = vol
