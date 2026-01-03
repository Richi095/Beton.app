import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ И СТИЛИ (ИСПРАВЛЕНО ДЛЯ МОБИЛЬНЫХ)
# ======================================================
# Добавлено initial_sidebar_state="collapsed" для корректной работы шторки
st.set_page_config(
    page_title="Бетон Завод PRO", 
    layout="wide", 
    page_icon="🏗️",
    initial_sidebar_state="collapsed" 
)

st.markdown("""
    <style>
    /* Основной фон */
    .stApp { background-color: #f8f9fc; }
    
    /* Исправление для мобильных: чтобы шторка не перекрывала клики */
    @media (max-width: 768px) {
        .st-emotion-cache-16idsys p { font-size: 14px; }
        div[data-testid="stSidebarCollapseButton"] { margin-bottom: 20px; }
    }

    /* Красивые карточки */
    div[data-testid="stVerticalBlock"] > div:has(div[style*="border"]) {
        background: white !important;
        padding: 20px !important;
        border-radius: 15px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        margin-bottom: 10px;
    }

    /* Кнопки */
    .stButton>button { border-radius: 8px; font-weight: 600; height: 3.5em; width: 100%; }
    
    /* WhatsApp Кнопка */
    .wa-button { 
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important; padding: 15px; border-radius: 10px;
        width: 100%; font-weight: bold; text-align: center;
        text-decoration: none; display: block; box-shadow: 0 4px 12px rgba(37,211,102,0.4);
    }
    </style>
    """, unsafe_allow_html=True)

DB_NAME = "database.db"

# ======================================================
# 2. ФУНКЦИИ БАЗЫ ДАННЫХ
# ======================================================
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
        conn.commit()

def get_list(table):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.execute(f"SELECT name FROM {table} ORDER BY name ASC").fetchall()
            return [r[0] for r in res]
    except: return []

init_db()

# ======================================================
# 3. АВТОРИЗАЦИЯ
# ======================================================
USERS = {"admin": "1234", "buh": "1111"}

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    _, col2, _ = st.columns([0.1, 0.8, 0.1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🏗️ БЕТОН ЗАВОД PRO</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            login = st.text_input("Логин")
            psw = st.text_input("Пароль", type="password")
            if st.button("Войти в систему"):
                if login in USERS and USERS[login] == psw:
                    st.session_state.update({"auth": True, "user": login})
                    st.rerun()
                else: st.error("❌ Ошибка доступа")
    st.stop()

# ======================================================
# 4. БОКОВОЕ МЕНЮ
# ======================================================
cur_user = st.session_state.user

with st.sidebar:
    st.title("⚙️ Настройки")
    st.write(f"Аккаунт: **{cur_user}**")
    
    if cur_user in ["admin", "buh"]:
        with st.expander("🚚 Водители", expanded=(cur_user == "buh")):
            new_drv = st.text_input("ФИО нового водителя")
            if st.button("➕ Добавить"):
                if new_drv:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv.strip(),))
                    st.rerun()
            st.divider()
            for drv in get_list("ref_drivers"):
                c_n, c_d = st.columns([4, 1])
                c_n.caption(drv)
                if c_d.button("🗑️", key=f"del_{drv}"):
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("DELETE FROM ref_drivers WHERE name = ?", (drv,))
                    st.rerun()

    if cur_user == "admin":
        with st.expander("🏭 Заводы и Марки"):
            new_plt = st.text_input("Новый завод")
            if st.button("➕ Завод"):
                if new_plt:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", (new_plt.strip(),))
                    st.rerun()
            st.divider()
            new_grd = st.text_input("Новая марка")
            if st.button("➕ Марка"):
                if new_grd:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_grd.strip(),))
                    st.rerun()

    st.divider()
    if st.button("🚪 Выйти"):
        st.session_state.clear()
        st.rerun()

# ======================================================
# 5. ГЛАВНЫЙ ИНТЕРФЕЙС
# ======================================================
PLANTS = get_list("ref_plants")
GRADES = get_list("ref_grades")
DRIVERS = get_list("ref_drivers")

t1, t2, t3, t4 = st.tabs(["📝 ОТГРУЗКА", "📖 ЖУРНАЛ", "🏗️ ОБЪЕКТЫ", "📈 АНАЛИТИКА"])

with t1:
    with st.container(border=True):
        st.markdown("### 🛠️ Новая накладная")
        p_sel = st.selectbox("Завод погрузки", PLANTS)
        obj_in = st.text_input("📍 Объект")
        g_sel = st.selectbox("💎 Марка бетона", GRADES)
        drvs_sel = st.multiselect("🚛 Выберите водителей", DRIVERS)

    if drvs_sel:
        st.subheader("📦 Детали")
        f1, f2 = st.columns(2)
        price = f1.number_input("Цена за м³", min_value=0, step=100)
        prepaid = f2.number_input("Предоплата", min_value=0, step=500)

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

        if st.button("💾 СОХРАНИТЬ", type="primary"):
            if obj_in and entries:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("INSERT INTO shipments (dt,tm,plant,object,grade,driver,volume,price_m3,total,paid,debt,invoice) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                st.session_state.last_wa = wa_text
                st.rerun()

        if "last_wa" in st.session_state:
            enc_text = urllib.parse.quote(st.session_state.last_wa)
            st.markdown(f'<a href="https://wa.me/?text={enc_text}" target="_blank" class="wa-button">📲 ОТПРАВИТЬ WHATSAPP</a>', unsafe_allow_html=True)

with t2:
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql("SELECT id, dt, tm, plant, object, driver, volume, total, debt FROM shipments ORDER BY id DESC", conn)
    st.dataframe(df, use_container_width=True, hide_index=True)

with t3:
    with sqlite3.connect(DB_NAME) as conn:
        df_obj = pd.read_sql("SELECT object, SUM(volume) as v, SUM(debt) as d FROM shipments GROUP BY object", conn)
    for _, r in df_obj.iterrows():
        with st.container(border=True):
            st.write(f"**📍 {r['object']}**")
            st.write(f"Объем: {r['v']} | Долг: {int(r['d']):,} ₸")

with t4:
    with sqlite3.connect(DB_NAME) as conn:
        df_an = pd.read_sql("SELECT dt, volume FROM shipments", conn)
    if not df_an.empty:
        st.area_chart(df_an.groupby('dt')['volume'].sum())
