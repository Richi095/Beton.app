import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import urllib.parse
import os

# ======================================================
# НАСТРОЙКИ
# ======================================================
st.set_page_config(
    page_title="Бетон Завод",
    layout="wide"
)

DB_FILE = "database.db"

USERS = {
    "director": {"password": "1234", "role": "director"},
    "buh": {"password": "1111", "role": "accountant"},
    "oper": {"password": "2222", "role": "operator"},
}

DRIVERS = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов",
    "Дмитрий Кузнецов", "Андрей Попов", "Михаил Новиков",
    "Артем Морозов", "Игорь Волков",
    "Виктор Васильев", "Николай Федоров"
]

# ======================================================
# DATABASE
# ======================================================
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    time TEXT,
    object TEXT,
    grade TEXT,
    driver TEXT,
    volume REAL,
    invoice TEXT,
    price REAL DEFAULT 0,
    paid REAL DEFAULT 0
)
""")
conn.commit()

# ======================================================
# AUTH
# ======================================================
if "auth" not in st.session_state:
    st.session_state.auth = False
if "role" not in st.session_state:
    st.session_state.role = None

if not st.session_state.auth:
    st.title("🔐 Вход")

    login = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")

    if st.button("Войти"):
        if login in USERS and USERS[login]["password"] == password:
            st.session_state.auth = True
            st.session_state.role = USERS[login]["role"]
            st.rerun()
        else:
            st.error("Неверные данные")
    st.stop()

# ======================================================
# UI
# ======================================================
st.title("🏗 Управление отгрузкой бетона")
st.caption(f"Роль: {st.session_state.role}")

tabs = ["🧱 Просмотр", "📊 Отчёты", "📈 Графики"]
if st.session_state.role in ["accountant", "director"]:
    tabs.insert(0, "📝 Отгрузка")
    tabs.append("💰 Оплаты")

tab = st.tabs(tabs)

# ======================================================
# 📝 ОТГРУЗКА
# ======================================================
if "📝 Отгрузка" in tabs:
    with tab[tabs.index("📝 Отгрузка")]:
        obj = st.text_input("Объект")
        grade = st.selectbox("Марка", ["М200","М250","М300","М350","М400"])
        drivers = st.multiselect("Водители", DRIVERS)

        for d in drivers:
            vol = st.number_input(f"{d} кубы", 0.0, step=0.5, key=f"v{d}")
            inv = st.text_input(f"{d} накладная", key=f"i{d}")
            price = st.number_input(f"{d} сумма", 0.0, step=100.0, key=f"p{d}")

            if st.button(f"Добавить {d}", key=f"b{d}"):
                cur.execute("""
                INSERT INTO shipments VALUES (
                    NULL,?,?,?,?,?,?,?,0
                )
                """, (
                    date.today().strftime("%d.%m.%Y"),
                    datetime.now().strftime("%H:%M"),
                    obj, grade, d, vol, inv, price
                ))
                conn.commit()
                st.success("Добавлено")

# ======================================================
# 🧱 ПРОСМОТР
# ======================================================
with tab[tabs.index("🧱 Просмотр")]:
    df = pd.read_sql("SELECT * FROM shipments", conn)
    st.dataframe(df, use_container_width=True)

# ======================================================
# 📊 ОТЧЁТЫ
# ======================================================
with tab[tabs.index("📊 Отчёты")]:
    d = st.date_input("Выберите дату", date.today())
    d_str = d.strftime("%d.%m.%Y")

    df = pd.read_sql("SELECT * FROM shipments WHERE date=?", conn, params=(d_str,))

    if df.empty:
        st.warning("Нет данных")
    else:
        st.metric("Объем", f"{df['volume'].sum()} м³")
        st.metric("Рейсов", len(df))

        st.subheader("По водителям")
        st.table(df.groupby("driver")["volume"].sum())

        st.subheader("По маркам")
        st.table(df.groupby("grade")["volume"].sum())

# ======================================================
# 📈 ГРАФИКИ
# ======================================================
with tab[tabs.index("📈 Графики")]:
    df = pd.read_sql("SELECT * FROM shipments", conn)

    if not df.empty:
        st.line_chart(df.groupby("date")["volume"].sum())
        st.bar_chart(df.groupby("driver")["volume"].sum())
        st.bar_chart(df.groupby("grade")["volume"].sum())

# ======================================================
# 💰 ОПЛАТЫ
# ======================================================
if "💰 Оплаты" in tabs:
    with tab[tabs.index("💰 Оплаты")]:
        df = pd.read_sql("SELECT * FROM shipments", conn)
        df["Долг"] = df["price"] - df["paid"]

        st.metric("Всего к оплате", df["price"].sum())
        st.metric("Оплачено", df["paid"].sum())
        st.metric("Долг", df["Долг"].sum())

        st.dataframe(df, use_container_width=True)

# ======================================================
# LOGOUT
# ======================================================
st.divider()
if st.button("🚪 Выйти"):
    st.session_state.clear()
    st.rerun()
