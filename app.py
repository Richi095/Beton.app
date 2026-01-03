import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ И СТИЛИ
# ======================================================
st.set_page_config(
    page_title="Бетон Завод PRO", 
    layout="wide", 
    page_icon="🏗️",
    initial_sidebar_state="collapsed" 
)

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fc; }
    div[data-testid="stVerticalBlock"] > div:has(div[style*="border"]) {
        background: white !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        margin-bottom: 10px;
    }
    .wa-button { 
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; padding: 18px; border-radius: 12px;
        width: 100%; font-weight: bold; text-align: center;
        text-decoration: none; display: block; margin-top: 10px;
    }
    .stButton>button { height: 3.5em; border-radius: 10px; font-weight: bold; width: 100%; }
    /* Стиль для кнопок удаления */
    .del-btn>button { height: 2em !important; background-color: #ff4b4b !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

DB_NAME = "database.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, plant TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT)""")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_drivers (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_grades (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_plants (name TEXT UNIQUE)")
        conn.executemany("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", [("УЧАСТОК",), ("888",)])
        default_grades = [("100",), ("150",), ("200",), ("250",), ("300",), ("350",), ("400",), ("Сухой замес",)]
        conn.executemany("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", default_grades)
        conn.commit()

def get_list(table):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.execute(f"SELECT name FROM {table} ORDER BY name ASC").fetchall()
            return [r[0] for r in res]
    except: return []

init_db()

# ======================================================
# 2. АВТОРИЗАЦИЯ
# ======================================================
USERS = {"admin": "1234", "buh": "1111"}

if "user" in st.query_params and not st.session_state.get("auth"):
    st.session_state.auth = True
    st.session_state.user = st.query_params["user"]

if not st.session_state.get("auth"):
    _, col2, _ = st.columns([0.1, 0.8, 0.1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🏗️ БЕТОН ЗАВОД PRO</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            l_in = st.text_input("Логин")
            p_in = st.text_input("Пароль", type="password")
            if st.button("ВОЙТИ"):
                if l_in in USERS and USERS[l_in] == p_in:
                    st.session_state.auth = True
                    st.session_state.user = l_in
                    st.query_params["user"] = l_in
                    st.rerun()
                else: st.error("❌ Ошибка")
    st.stop()

# ======================================================
# 3. БОКОВОЕ МЕНЮ (ИСПРАВЛЕННОЕ УПРАВЛЕНИЕ ВОДИТЕЛЯМИ)
# ======================================================
cur_user = st.session_state.user
with st.sidebar:
    st.title("⚙️ Настройки")
    if st.button("🚪 Выйти"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    
    st.divider()
    if cur_user in ["admin", "buh"]:
        st.subheader("🚚 Водители")
        new_drv_name = st.text_input("ФИО водителя", key="input_new_drv")
        if st.button("➕ Добавить водителя", key="btn_add_drv"):
            if new_drv_name:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv_name.strip(),))
                st.rerun()
        
        st.write("---")
        current_drivers = get_list("ref_drivers")
        for d in current_drivers:
            c1, c2 = st.columns([4, 1])
            c1.caption(d)
            if c2.button("🗑️", key=f"del_drv_{d}"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM ref_drivers WHERE name=?", (d,))
                st.rerun()

    if cur_user == "admin":
        st.divider()
        st.subheader("🏭 Заводы и Марки")
        new_g = st.text_input("Новая марка")
        if st.button("➕ Добавить марку"):
            if new_g:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_g.strip(),))
                st.rerun()

# ======================================================
# 4. ГЛАВНЫЙ ИНТЕРФЕЙС
# ======================================================
PLANTS = get_list("ref_plants")
GRADES = get_list("ref_grades")
DRIVERS = get_list("ref_drivers")

t1, t2, t3, t4 = st.tabs(["📝 ОТГРУЗКА", "📖 ЖУРНАЛ", "🏗️ ОБЪЕКТЫ", "📈 АНАЛИТИКА"])

with t1:
    # Кнопка сброса
    if st.session_state.get("submitted"):
        if st.button("➕ ОЧИСТИТЬ И НОВАЯ ЗАЯВКА", type="primary"):
            st.session_state.submitted = False
            if "last_msg" in st.session_state: del st.session_state.last_msg
            st.rerun()

    # Основная форма
    if not st.session_state.get("submitted"):
        with st.container(border=True):
            st.markdown("### 🛠️ Новая накладная")
            p_sel = st.selectbox("Завод погрузки", PLANTS)
            obj_in = st.text_input("📍 Объект")
            g_sel = st.selectbox("💎 Марка бетона", GRADES)
            drvs_sel = st.multiselect("🚛 Выберите водителей", DRIVERS)

        if drvs_sel:
            st.subheader("📦 Объемы")
            f1, f2 = st.columns(2)
            price = f1.number_input("Цена за м³", min_value=0, step=100)
            prepaid = f2.number_input("Общая предоплата", min_value=0, step=500)

            entries = []
            wa_text = f"🏗️ *БЕТОН-ЗАВОД*\n🏭 Завод: {p_sel}\n📍 Объект: {obj_in}\n💎 Марка: {g_sel}\n────────────────\n"
            
            for d in drvs_sel:
                with st.container(border=True):
                    ca, cb = st.columns([2, 1])
                    v = ca.number_input(f"м³ ({d})", min_value=0.0, step=0.1, key=f"v_{d}")
                    inv = cb.text_input(f"Накл. №", key=f"inv_{d}")
                    if v > 0:
                        total = v * price
                        paid = prepaid / len(drvs_sel) if prepaid > 0 else 0
                        entries.append((date.today().isoformat(), datetime.now().strftime("%H:%M"), p_sel, obj_in, g_sel, d, v, price, total, paid, total-paid, inv))
                        wa_text += f"🚛 {d}: *{v} м³* (№{inv})\n"

            if st.button("💾 СОХРАНИТЬ В БАЗУ"):
                if obj_in and entries:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.executemany("INSERT INTO shipments (dt,tm,plant,object,grade,driver,volume,price_m3,total,paid,debt,invoice) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                    st.session_state.last_msg = wa_text
                    st.session_state.submitted = True
                    st.rerun()
                else: st.warning("Заполните данные")

    # Вывод кнопки WhatsApp после сохранения
    if st.session_state.get("submitted") and "last_msg" in st.session_state:
        enc_text = urllib.parse.quote(st.session_state.last_msg)
        st.markdown(f'<a href="https://wa.me/?text={enc_text}" target="_blank" class="wa-button">📲 ОТПРАВИТЬ В WHATSAPP</a>', unsafe_allow_html=True)

with t2:
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql("SELECT id, dt, tm, plant, object, driver, volume, total, debt FROM shipments ORDER BY id DESC LIMIT 100", conn)
    st.dataframe(df, use_container_width=True, hide_index=True)

with t3:
    with sqlite3.connect(DB_NAME) as conn:
        df_obj = pd.read_sql("SELECT object, SUM(volume) as v, SUM(debt) as d FROM shipments GROUP BY object", conn)
    for _, r in df_obj.iterrows():
        with st.container(border=True):
            st.write(f"**📍 {r['object']}** | Объем: {r['v']:.1f} м³ | Долг: {int(r['d']):,} ₸")
