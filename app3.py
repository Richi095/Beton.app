import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
import hashlib
from datetime import datetime, date

# ======================================================
# 1. НАСТРОЙКИ И БЕЗОПАСНОСТЬ (Пункт 3)
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide")

DB_NAME = "database.db"

# Функция для создания хэша пароля
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Данные пользователей (теперь с хэшами)
USERS = {
    "director": {"hash": hash_password("1234"), "role": "director"},
    "buh": {"hash": hash_password("1111"), "role": "accountant"},
    "oper": {"hash": hash_password("2222"), "role": "operator"},
}

# ======================================================
# 2. РАБОТА С БД (Пункт 1)
# ======================================================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        # Основная таблица отгрузок
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT, msg TEXT
        )""")
        # Справочник водителей
        conn.execute("CREATE TABLE IF NOT EXISTS ref_drivers (name TEXT UNIQUE)")
        # Справочник марок бетона
        conn.execute("CREATE TABLE IF NOT EXISTS ref_grades (name TEXT UNIQUE)")

def get_list(table):
    with sqlite3.connect(DB_NAME) as conn:
        res = conn.execute(f"SELECT name FROM {table}").fetchall()
        return [r[0] for r in res]

init_db()

# ======================================================
# 3. АВТОРИЗАЦИЯ
# ======================================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Вход в систему")
    login = st.text_input("Логин")
    psw = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if login in USERS and USERS[login]["hash"] == hash_password(psw):
            st.session_state.update({"auth": True, "user": login, "role": USERS[login]["role"]})
            st.rerun()
        else:
            st.error("Ошибка входа")
    st.stop()

# ======================================================
# 4. ИНТЕРФЕЙС
# ======================================================
st.sidebar.write(f"👤 {st.session_state.user} ({st.session_state.role})")
if st.sidebar.button("Выход"):
    st.session_state.clear()
    st.rerun()

# Список вкладок (Добавлена Настройки)
tabs = ["📝 Отгрузка", "📊 Отчёты", "📈 Графики", "🚛 Водители", "⚙️ Настройки"]
t1, t2, t3, t4, t5 = st.tabs(tabs)

# Загружаем списки из БД
DRIVERS_LIST = get_list("ref_drivers")
GRADES_LIST = get_list("ref_grades")

# --- ВКЛАДКА: ОТГРУЗКА ---
with t1:
    if not DRIVERS_LIST or not GRADES_LIST:
        st.warning("Сначала добавьте водителей и марки в 'Настройках'")
    else:
        st.subheader("Новая запись")
        c1, c2 = st.columns(2)
        obj = c1.text_input("📍 Объект")
        grade = c1.selectbox("💎 Марка", GRADES_LIST)
        selected = c2.multiselect("🚛 Водители", DRIVERS_LIST)

        # ... (логика расчета остается прежней)
        price, paid = 0.0, 0.0
        if st.session_state.role in ["accountant", "director"]:
            f1, f2 = st.columns(2)
            price = f1.number_input("Цена за м³", min_value=0.0, step=100.0)
            paid = f2.number_input("Оплачено итого", min_value=0.0, step=500.0)

        entries = []
        report_text = f"🏗 *ОТГРУЗКА БЕТОНА*\n📍 *Объект:* {obj}\n💎 *Марка:* {grade}\n────────────\n"

        for d in selected:
            sc1, sc2, sc3 = st.columns([2, 1, 1])
            with sc1: st.write(f"**{d}**")
            vol = sc2.number_input("м³", 0.0, step=0.5, key=f"v_{d}")
            inv = sc3.text_input("№ Накл.", key=f"i_{d}")
            
            if vol > 0:
                total = vol * price
                debt = total - (paid / len(selected) if (paid > 0 and len(selected) > 0) else 0)
                now = datetime.now()
                entries.append([
                    now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                    obj, grade, d, vol, price, total, paid, debt, inv, ""
                ])
                report_text += f"🚛 {d}: *{vol} м³* (№{inv})\n"

        if st.button("💾 Сохранить"):
            if not obj or not entries:
                st.warning("Заполните данные")
            else:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("INSERT INTO shipments (dt, tm, object, grade, driver, volume, price_m3, total, paid, debt, invoice, msg) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                st.success("Данные сохранены")
                st.session_state.last_wa = report_text

# --- ВКЛАДКА: ОТЧЕТЫ С ФИЛЬТРАМИ (Пункт 2) ---
with t2:
    st.subheader("Фильтры")
    fc1, fc2, fc3 = st.columns(3)
    f_date = fc1.date_input("Дата", date.today())
    f_obj = fc2.text_input("По объекту")
    f_drv = fc3.selectbox("По водителю", ["Все"] + DRIVERS_LIST)

    query = "SELECT * FROM shipments WHERE dt = ?"
    params = [str(f_date)]

    if f_obj:
        query += " AND object LIKE ?"
        params.append(f"%{f_obj}%")
    if f_drv != "Все":
        query += " AND driver = ?"
        params.append(f_drv)

    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql(query, conn, params=params)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        # Суммарные показатели
        st.metric("Итого объем", f"{df['volume'].sum()} м³")
        st.metric("Общий долг", f"{df['debt'].sum():,.2f} руб.")
    else:
        st.info("Данных не найдено")

# --- ВКЛАДКА: НАСТРОЙКИ (Пункт 1) ---
with t5:
    if st.session_state.role != "director":
        st.error("Доступ только для Директора")
    else:
        st.subheader("Управление справочниками")
        col_a, col_b = st.columns(2)
        
        with col_a:
            new_drv = st.text_input("Новый водитель")
            if st.button("Добавить водителя"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv,))
                    st.rerun()
            st.write(DRIVERS_LIST)

        with col_b:
            new_grd = st.text_input("Новая марка")
            if st.button("Добавить марку"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_grd,))
                    st.rerun()
            st.write(GRADES_LIST)
        
        if st.button("📥 Скачать бэкап БД"):
            with open(DB_NAME, "rb") as f:
                st.download_button("Подтвердить скачивание", f, file_name="backup.db")
