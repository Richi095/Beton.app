import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. НАСТРОЙКИ
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide")

DB_NAME = "database.db"

USERS = {
    "director": {"password": "1234", "role": "director"},
    "buh": {"password": "1111", "role": "accountant"},
    "oper": {"password": "2222", "role": "operator"},
}
DRIVERS = ["Иванов", "Соколов", "Андреев", "Петров", "Кузнецов", "Морозов"]

# ======================================================
# 2. БД
# ======================================================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT, msg TEXT
        )
        """)

def save_to_db(records):
    with sqlite3.connect(DB_NAME) as conn:
        conn.executemany("""
        INSERT INTO shipments 
        (dt, tm, object, grade, driver, volume, price_m3, total, paid, debt, invoice, msg)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, records)

init_db()

# ======================================================
# 3. АВТОРИЗАЦИЯ
# ======================================================
if "auth" not in st.session_state:
    params = st.query_params
    if "user" in params and params["user"] in USERS:
        u = params["user"]
        st.session_state.update({"auth": True, "user": u, "role": USERS[u]["role"]})
    else:
        st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Вход")
    login = st.text_input("Логин")
    psw = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if login in USERS and USERS[login]["password"] == psw:
            st.query_params["user"] = login
            st.session_state.update({"auth": True, "user": login, "role": USERS[login]["role"]})
            st.rerun()
        else:
            st.error("Ошибка входа")
    st.stop()

# ======================================================
# 4. ИНТЕРФЕЙС
# ======================================================
st.sidebar.write(f"👤 {st.session_state.user}")
if st.sidebar.button("Выход"):
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

t1, t2, t3, t4 = st.tabs(["📝 Отгрузка", "📊 Отчёты", "📈 Графики", "🚛 Водители"])

# --- ВКЛАДКА: ОТГРУЗКА ---
with t1:
    st.subheader("Новая запись")
    c1, c2 = st.columns(2)
    obj = c1.text_input("📍 Объект")
    grade = c1.selectbox("💎 Марка", ["М200", "М250", "М300", "М350", "М400"])
    selected = c2.multiselect("🚛 Водители", DRIVERS)

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
            debt = total - (paid / len(selected) if paid > 0 else 0)
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
            for e in entries: e[11] = report_text
            save_to_db(entries)
            st.success("Данные сохранены")
            st.session_state.last_wa = report_text

    if "last_wa" in st.session_state:
        wa_url = f"https://wa.me/?text={urllib.parse.quote(st.session_state.last_wa)}"
        st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25D366; color:white; border:none; padding:10px; border-radius:5px; width:100%; cursor:pointer;">📲 ОТПРАВИТЬ В WHATSAPP</button></a>', unsafe_allow_html=True)

# --- ВКЛАДКА: ОТЧЕТЫ (ИСПРАВЛЕННЫЙ EXCEL) ---
with t2:
    rep_date = st.date_input("Дата", date.today())
    query = """
    SELECT dt as 'Дата', tm as 'Время', object as 'Объект', grade as 'Марка', 
    driver as 'Водитель', volume as 'Объем', price_m3 as 'Цена', 
    total as 'Сумма', paid as 'Оплачено', debt as 'Долг', invoice as 'Накладная'
    FROM shipments WHERE dt=?
    """
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql(query, conn, params=(str(rep_date),))

    if not df.empty:
        # СОЗДАНИЕ EXCEL
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Отчет')
            # Настройка колонок
            sheet = writer.sheets['Отчет']
            for i, col in enumerate(df.columns):
                sheet.set_column(i, i, 15)
        
        # ВАЖНО: Возвращаем каретку в начало буфера
        buf.seek(0)
        
        st.download_button(
            label="📥 СКАЧАТЬ EXCEL (.xlsx)",
            data=buf,
            file_name=f"beton_{rep_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Нет данных за эту дату")

# --- ВКЛАДКА: ГРАФИКИ ---
with t3:
    with sqlite3.connect(DB_NAME) as conn:
        df_all = pd.read_sql("SELECT driver, volume, object FROM shipments", conn)
    if not df_all.empty:
        st.write("### По водителям (м³)")
        st.bar_chart(df_all.groupby("driver")["volume"].sum())
        st.write("### По объектам (м³)")
        st.bar_chart(df_all.groupby("object")["volume"].sum())

# --- ВКЛАДКА: ВОДИТЕЛИ ---
with t4:
    with sqlite3.connect(DB_NAME) as conn:
        df_d = pd.read_sql("SELECT driver, SUM(volume) as 'Всего м3', COUNT(id) as 'Рейсов' FROM shipments GROUP BY driver", conn)
    st.table(df_d)
