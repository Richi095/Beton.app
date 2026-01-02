import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, date
import urllib.parse

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Бетон Завод", layout="wide")

DB = "database.db"

USERS = {
    "director": {"password": "1234", "role": "director"},
    "buh": {"password": "1111", "role": "accountant"},
    "oper": {"password": "2222", "role": "operator"},
}

DRIVERS = [
    "Алексей Петров","Иван Иванов","Сергей Соколов",
    "Дмитрий Кузнецов","Андрей Попов","Михаил Новиков",
    "Артем Морозов","Игорь Волков","Виктор Васильев","Николай Федоров"
]

# ======================================================
# DB
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
invoice TEXT,
msg TEXT
)
""")
conn.commit()

# ======================================================
# AUTO LOGIN (COOKIE via QUERY PARAM)
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
            st.error("Неверные данные")
    st.stop()

# ======================================================
# UI
# ======================================================
st.title("🏗 Управление отгрузкой бетона")
st.caption(f"Пользователь: {st.session_state.user}")

tabs = st.tabs(["📝 Отгрузка", "📊 Отчёты", "🚛 Водители"])

# ======================================================
# 📝 ОТГРУЗКА + WHATSAPP
# ======================================================
with tabs[0]:
    obj = st.text_input("Объект")
    grade = st.selectbox("Марка", ["М200","М250","М300","М350","М400"])
    sel = st.multiselect("Водители", DRIVERS)

    report = f"🏗 *ОТГРУЗКА БЕТОНА*\n📍 *Объект:* {obj}\n💎 *Марка:* {grade}\n────────────\n"

    for d in sel:
        v = st.number_input(f"{d} м³", 0.0, step=0.5, key=f"v{d}")
        n = st.text_input(f"{d} накладная", key=f"n{d}")
        if v > 0:
            report += f"🚛 {d}: *{v} м³* (№{n})\n"

    if st.button("💾 Сохранить заявку"):
        cur.execute("""
        INSERT INTO shipments VALUES(NULL,?,?,?,?,?,?,?,?)
        """, (
            date.today().strftime("%d.%m.%Y"),
            datetime.now().strftime("%H:%M"),
            obj, grade, ",".join(sel), 0, "", report
        ))
        conn.commit()
        st.success("Заявка сохранена")

    # 🔥 КНОПКА WHATSAPP — ВСЕГДА
    last = cur.execute("SELECT msg FROM shipments ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        msg = last[0]
        st.subheader("📲 Отправка в WhatsApp")
        st.code(msg)
        url = "https://wa.me/?text=" + urllib.parse.quote(msg)
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
    d = st.date_input("Дата", date.today())
    df = pd.read_sql("SELECT * FROM shipments WHERE dt=?", conn,
                     params=(d.strftime("%d.%m.%Y"),))
    st.dataframe(df, use_container_width=True)

# ======================================================
# 🚛 ВОДИТЕЛИ
# ======================================================
with tabs[2]:
    df = pd.read_sql("SELECT driver,COUNT(*) рейсов FROM shipments GROUP BY driver", conn)
    st.table(df)

# ======================================================
# LOGOUT
# ======================================================
st.divider()
if st.button("🚪 Выйти"):
    st.experimental_set_query_params()
    st.session_state.clear()
    st.rerun()
