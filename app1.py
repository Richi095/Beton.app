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
# 🔥 CLEAN OLD MULTIDRIVER RECORDS
# ======================================================
rows = cur.execute(
    "SELECT id, driver, volume, price_m3, total, paid, debt, invoice, dt, tm, object, grade, msg FROM shipments WHERE driver LIKE '%,%'"
).fetchall()

for r in rows:
    drivers = [d.strip() for d in r[1].split(",")]
    for d in drivers:
        cur.execute("""
        INSERT INTO shipments
        (dt, tm, object, grade, driver, volume,
         price_m3, total, paid, debt, invoice, msg)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (r[8], r[9], r[10], r[11], d,
              r[2], r[3], r[4], r[5], r[6], r[7], r[12]))
    cur.execute("DELETE FROM shipments WHERE id=?", (r[0],))
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
            total = vol * price
            debt = total - paid
            entries.append((d, vol, price, total, paid, debt, inv))
            report += f"🚛 {d}: *{vol} м³* × {price}₸ = *{total}₸* (№{inv})\n"

    if st.button("💾 Сохранить заявку"):
        if not obj or not entries:
            st.error("Заполните объект и данные водителей")
        else:
            for d, vol, price, total, paid, debt, inv in entries:
                cur.execute("""
                INSERT INTO shipments
                (dt, tm, object, grade, driver, volume,
                 price_m3, total, paid, debt, invoice, msg)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    date.today().strftime("%d.%m.%Y"),
                    datetime.now().strftime("%H:%M"),
                    obj, grade, d, vol,
                    price, total, paid, debt, inv, report
                ))
            conn.commit()
            st.success(f"Сохранено рейсов: {len(entries)}")

    # ===== WhatsApp (последняя заявка) =====
    last = cur.execute("SELECT msg FROM shipments ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        st.subheader("📲 Отправка в WhatsApp")
        st.code(last[0])
        url = "https://wa.me/?text=" + urllib.parse.quote(last[0])
        st.markdown(f"""
        <a href="{url}" target="_blank">
        <button style="width:100%;background:#25D366;color:white;
        padding:15px;border:none;border-radius:10px;font-size:18px;">
        🟢 ОТПРАВИТЬ В WHATSAPP
        </button></a>
        """, unsafe_allow_html=True)

# ======================================================
# 📊 ОТЧЁТЫ
# ======================================================
with tabs[1]:
    d = st.date_input("Дата отчёта", date.today())
    df = pd.read_sql(
        "SELECT * FROM shipments WHERE dt=?",
        conn,
        params=(d.strftime("%d.%m.%Y"),)
    )

    if df.empty:
        st.warning("Нет данных за выбранную дату")
    else:
        st.metric("Объём, м³", df["volume"].sum())
        st.metric("Сумма ₸", df["total"].sum())
        st.metric("Оплачено ₸", df["paid"].sum())
        st.metric("Долг ₸", df["debt"].sum())
        st.dataframe(df, use_container_width=True)

# ======================================================
# 📈 ГРАФИКИ
# ======================================================
with tabs[2]:
    df = pd.read_sql("SELECT * FROM shipments", conn)
    if not df.empty:
        st.bar_chart(df.groupby("driver")["volume"].sum())
        st.bar_chart(df.groupby("object")["total"].sum())

# ======================================================
# 🚛 ВОДИТЕЛИ
# ======================================================
with tabs[3]:
    df = pd.read_sql("""
        SELECT driver,
               SUM(volume) AS м3,
               SUM(total) AS сумма,
               SUM(debt) AS долг
        FROM shipments
        GROUP BY driver
    """, conn)
    st.table(df)

# ======================================================
# LOGOUT
# ======================================================
st.divider()
if st.button("🚪 Выйти"):
    st.experimental_set_query_params()
    st.session_state.clear()
    st.rerun()
