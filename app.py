import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ И СТИЛИ
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide", page_icon="🏗️")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fc; }
    div[data-testid="stVerticalBlock"] > div:has(div[style*="border"]) {
        background: white !important;
        padding: 25px !important;
        border-radius: 15px !important;
        border: none !important;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
        margin-bottom: 10px;
    }
    .stButton>button { border-radius: 8px; font-weight: 600; height: 3em; }
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
        
        # Начальные настройки заводов
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
# 3. АВТОРИЗАЦИЯ (ОБНОВЛЕННЫЕ ПОЛЬЗОВАТЕЛИ)
# ======================================================
USERS = {
    "admin": "1234",
    "buh": "1111"
}

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🏗️ БЕТОН ЗАВОД PRO</h1>", unsafe_allow_html=True)
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
# 4. БОКОВОЕ МЕНЮ (ПРАВА ДОСТУПА)
# ======================================================
cur_user = st.session_state.user

with st.sidebar:
    st.title("⚙️ Настройки")
    st.write(f"Пользователь: **{cur_user}**")
    
    # Секция для БУХГАЛТЕРА и АДМИНА (только водители)
    if cur_user in ["admin", "buh"]:
        with st.expander("🚚 Управление водителями", expanded=True):
            new_drv = st.text_input("ФИО нового водителя")
            if st.button("➕ Добавить"):
                if new_drv:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv.strip(),))
                    st.rerun()
            
            st.divider()
            st.caption("Список и удаление:")
            all_drivers = get_list("ref_drivers")
            for drv in all_drivers:
                c_n, c_d = st.columns([4, 1])
                c_n.write(drv)
                if c_d.button("🗑️", key=f"del_{drv}"):
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("DELETE FROM ref_drivers WHERE name = ?", (drv,))
                    st.rerun()

    # Секция ТОЛЬКО для АДМИНА (заводы и марки)
    if cur_user == "admin":
        with st.expander("🏭 Заводы и Марки"):
            st.caption("Заводы")
            new_plt = st.text_input("Название завода")
            if st.button("➕ Добавить завод"):
                if new_plt:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", (new_plt.strip(),))
                    st.rerun()
            
            st.divider()
            st.caption("Марки бетона")
            new_grd = st.text_input("Название марки")
            if st.button("➕ Добавить марку"):
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

# --- ВКЛАДКА 1: ОТГРУЗКА ---
with t1:
    with st.container(border=True):
        st.subheader("🛠️ Новая накладная")
        c1, c2, c3 = st.columns(3)
        p_sel = c1.selectbox("Завод погрузки", PLANTS if PLANTS else ["Добавьте заводы в настройках"])
        obj_in = c2.text_input("📍 Объект (стройплощадка)")
        g_sel = c3.selectbox("💎 Марка бетона", GRADES if GRADES else ["Добавьте марки"])
        drvs_sel = st.multiselect("🚛 Выберите водителей", DRIVERS)

    if drvs_sel:
        st.subheader("📦 Объемы и оплата")
        f1, f2 = st.columns(2)
        price = f1.number_input("Цена за м³", min_value=0, step=100, format="%d")
        prepaid = f2.number_input("Общая предоплата", min_value=0, step=500, format="%d")

        entries = []
        wa_text = f"🏗️ *БЕТОН-ЗАВОД*\n🏭 Завод: {p_sel}\n📍 Объект: {obj_in}\n💎 Марка: {g_sel}\n────────────────\n"
        
        grid = st.columns(2)
        for idx, d in enumerate(drvs_sel):
            with grid[idx % 2]:
                with st.container(border=True):
                    ca, cb = st.columns([2, 1])
                    v = ca.number_input(f"м³ ({d})", min_value=0.0, step=0.1, key=f"v_{d}")
                    inv = cb.text_input(f"Накл. №", key=f"inv_{d}")
                    if v > 0:
                        total = v * price
                        paid = prepaid / len(drvs_sel) if prepaid > 0 else 0
                        entries.append((date.today().isoformat(), datetime.now().strftime("%H:%M"), p_sel, obj_in, g_sel, d, v, price, total, paid, total-paid, inv))
                        wa_text += f"🚛 {d}: *{v} м³* (№{inv})\n"

        if st.button("💾 СОХРАНИТЬ В БАЗУ", type="primary"):
            if not obj_in or not entries:
                st.warning("Заполните объект и объем")
            else:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("INSERT INTO shipments (dt,tm,plant,object,grade,driver,volume,price_m3,total,paid,debt,invoice) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                st.session_state.last_wa = wa_text
                st.success("✅ Данные успешно сохранены!")
                st.rerun()

        if "last_wa" in st.session_state:
            enc_text = urllib.parse.quote(st.session_state.last_wa)
            st.markdown(f'<a href="https://wa.me/?text={enc_text}" target="_blank" class="wa-button">📲 ОТПРАВИТЬ В WHATSAPP</a>', unsafe_allow_html=True)

# Оставшиеся вкладки (Журнал, Сводка, Аналитика)
with t2:
    st.subheader("📖 История отгрузок")
    with sqlite3.connect(DB_NAME) as conn:
        df_log = pd.read_sql("SELECT id, dt, tm, plant, object, driver, volume, total, debt FROM shipments ORDER BY id DESC", conn)
    st.dataframe(df_log, use_container_width=True, hide_index=True)

with t3:
    st.subheader("🏗️ Состояние по объектам")
    with sqlite3.connect(DB_NAME) as conn:
        df_obj = pd.read_sql("SELECT object, SUM(volume) as v, SUM(total) as t, SUM(paid) as p, SUM(debt) as d FROM shipments GROUP BY object", conn)
    if not df_obj.empty:
        grid_obj = st.columns(3)
        for idx, r in df_obj.iterrows():
            with grid_obj[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"### 📍 {r['object']}")
                    st.metric("Отгружено", f"{r['v']:.1f} м³")
                    st.metric("Долг", f"{int(r['d']):,} ₸")
                    prog = min(r['p']/r['t'], 1.0) if r['t'] > 0 else 0
                    st.progress(prog)
    else: st.info("Нет данных")

with t4:
    st.subheader("📈 Краткая аналитика")
    with sqlite3.connect(DB_NAME) as conn:
        df_an = pd.read_sql("SELECT dt, volume, total FROM shipments", conn)
    if not df_an.empty:
        st.area_chart(df_an.groupby('dt')['volume'].sum())
    else: st.info("Данных нет")
