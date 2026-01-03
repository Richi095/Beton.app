import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ, СТИЛИ И БРЕНДИНГ
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide", page_icon="🏗️")

st.markdown("""
    <style>
    /* Основной фон и шрифты */
    .stApp { background-color: #f8f9fc; }
    
    /* Стилизация карточек */
    div[data-testid="stVerticalBlock"] > div:has(div[style*="border"]) {
        background: white !important;
        padding: 25px !important;
        border-radius: 15px !important;
        border: none !important;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
    }

    /* Метрики */
    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px !important;
        border-radius: 12px;
    }

    /* Кнопки */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
        transition: 0.3s;
    }
    
    /* WhatsApp Кнопка */
    .wa-button { 
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important;
        padding: 15px;
        border-radius: 10px;
        width: 100%;
        font-weight: bold;
        text-align: center;
        text-decoration: none;
        display: block;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.4);
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
        
        # Начальные данные
        conn.executemany("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", [("Завод №1",), ("Завод №2",)])
        conn.executemany("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", [("М200",), ("М300",), ("М400",)])
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
USERS = {"admin": "admin", "director": "1234", "oper": "1111"}

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🏗️ ВХОД В СИСТЕМУ</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            login = st.text_input("Логин")
            psw = st.text_input("Пароль", type="password")
            if st.button("Войти"):
                if login in USERS and USERS[login] == psw:
                    st.session_state.update({"auth": True, "user": login})
                    st.rerun()
                else: st.error("Неверные данные")
    st.stop()

# ======================================================
# 4. БОКОВОЕ МЕНЮ (НАСТРОЙКИ)
# ======================================================
with st.sidebar:
    st.title("⚙️ Настройки")
    st.write(f"Пользователь: **{st.session_state.user}**")
    
    if st.session_state.user in ["admin", "director"]:
        with st.expander("🏭 Справочники"):
            # Управление заводами
            new_plt = st.text_input("Добавить завод")
            if st.button("➕ Завод"):
                if new_plt:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", (new_plt.strip(),))
                    st.rerun()
            
            # Управление водителями
            new_drv = st.text_input("Добавить водителя")
            if st.button("➕ Водитель"):
                if new_drv:
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv.strip(),))
                    st.rerun()
    
    if st.button("🚪 Выйти"):
        st.session_state.clear()
        st.rerun()

# ======================================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС
# ======================================================
PLANTS = get_list("ref_plants")
GRADES = get_list("ref_grades")
DRIVERS = get_list("ref_drivers")

t1, t2, t3, t4 = st.tabs(["📝 ОТГРУЗКА", "📖 ЖУРНАЛ", "🏗️ ОБЪЕКТЫ", "📈 АНАЛИТИКА"])

# --- ВКЛАДКА 1: ОТГРУЗКА ---
with t1:
    with st.container(border=True):
        st.subheader("🛠️ Создание накладной")
        c1, c2, c3 = st.columns(3)
        p_sel = c1.selectbox("Завод", PLANTS)
        obj_in = c2.text_input("Объект строительства")
        g_sel = c3.selectbox("Марка бетона", GRADES)
        
        drvs_sel = st.multiselect("Выберите водителей (машины)", DRIVERS)

    if drvs_sel:
        st.subheader("🚛 Детализация рейсов")
        f1, f2 = st.columns(2)
        price = f1.number_input("Цена за м³", min_value=0, step=100)
        prepaid = f2.number_input("Общая предоплата", min_value=0, step=500)

        entries = []
        wa_text = f"🏗️ *ОТГРУЗКА БЕТОНА*\n📍 Объект: {obj_in}\n💎 Марка: {g_sel}\n"
        
        grid = st.columns(2)
        for idx, d in enumerate(drvs_sel):
            with grid[idx % 2]:
                with st.container(border=True):
                    ca, cb = st.columns([2, 1])
                    v = ca.number_input(f"Объем {d}", min_value=0.0, step=0.1, key=f"v_{d}")
                    inv = cb.text_input(f"Накл. №", key=f"inv_{d}")
                    if v > 0:
                        total = v * price
                        paid = prepaid / len(drvs_sel) if prepaid > 0 else 0
                        entries.append((date.today().isoformat(), datetime.now().strftime("%H:%M"), p_sel, obj_in, g_sel, d, v, price, total, paid, total-paid, inv))
                        wa_text += f"🚛 {d}: *{v} м³* (№{inv})\n"

        if st.button("💾 СОХРАНИТЬ И СФОРМИРОВАТЬ СООБЩЕНИЕ", type="primary"):
            if not obj_in or not entries:
                st.warning("Заполните объект и объемы!")
            else:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("INSERT INTO shipments (dt,tm,plant,object,grade,driver,volume,price_m3,total,paid,debt,invoice) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                st.session_state.last_wa = wa_text
                st.success("Данные сохранены!")
                st.rerun()

        if "last_wa" in st.session_state:
            enc_text = urllib.parse.quote(st.session_state.last_wa)
            st.markdown(f'<a href="https://wa.me/?text={enc_text}" target="_blank" class="wa-button">📲 ОТПРАВИТЬ В WHATSAPP</a>', unsafe_allow_html=True)

# --- ВКЛАДКА 3: ОБЪЕКТЫ (СВОДКА) ---
with t3:
    st.subheader("🏗️ Состояние расчетов")
    with sqlite3.connect(DB_NAME) as conn:
        df_obj = pd.read_sql("SELECT object, SUM(volume) as v, SUM(total) as t, SUM(paid) as p, SUM(debt) as d FROM shipments GROUP BY object", conn)
    
    if not df_obj.empty:
        grid_obj = st.columns(3)
        for idx, r in df_obj.iterrows():
            with grid_obj[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"#### 📍 {r['object']}")
                    st.metric("Отгружено", f"{r['v']:.1f} м³")
                    st.metric("Долг", f"{int(r['d']):,} ₸", delta=f"{int(r['t']):,} всего", delta_color="inverse")
                    prog = min(r['p']/r['t'], 1.0) if r['t'] > 0 else 0
                    st.progress(prog, text=f"Оплачено {prog:.0%}")
    else: st.info("Нет данных")

# --- ВКЛАДКА 4: АНАЛИТИКА ---
with t4:
    with sqlite3.connect(DB_NAME) as conn:
        df_an = pd.read_sql("SELECT dt, volume, total FROM shipments", conn)
    
    if not df_an.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Всего м³", f"{df_an['volume'].sum():.1f}")
        c2.metric("Выручка", f"{int(df_an['total'].sum()):,}")
        c3.metric("Машин", len(df_an))
        
        st.divider()
        st.area_chart(df_an.groupby('dt')['volume'].sum())
    else: st.info("Добавьте данные для графиков")

# Вкладка Журнал (упрощенно для экономии места)
with t2:
    with sqlite3.connect(DB_NAME) as conn:
        df_log = pd.read_sql("SELECT * FROM shipments ORDER BY id DESC", conn)
    st.dataframe(df_log, use_container_width=True, hide_index=True)
