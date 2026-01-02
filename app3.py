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
    .stApp { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .wa-button { 
        background-color: #25D366; color: white; border: none; padding: 15px; 
        border-radius: 10px; width: 100%; font-weight: bold; cursor: pointer; 
        text-align: center; text-decoration: none; display: block; margin-top: 10px;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

DB_NAME = "database.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, plant TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT, msg TEXT)""")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_drivers (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_grades (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_plants (name TEXT UNIQUE)")
        
        default_plants = [("Участок",), ("888",)]
        conn.executemany("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", default_plants)
        default_grades = [("М100",), ("М150",), ("М200",), ("М250",), ("М300",), ("М350",), ("М400",)]
        conn.executemany("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", default_grades)
        conn.commit()

def get_list(table):
    allowed = ["ref_drivers", "ref_grades", "ref_plants"]
    if table not in allowed: return []
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.execute(f"SELECT name FROM {table} ORDER BY name ASC").fetchall()
            return [r[0] for r in res]
    except: return []

init_db()

# ======================================================
# 2. АВТОРИЗАЦИЯ
# ======================================================
USERS = {"director": "1234", "buh": "1111", "oper": "2222", "admin": "admin"}

query_params = st.query_params
if "logged_in" in query_params and "auth" not in st.session_state:
    user_from_url = query_params["logged_in"]
    if user_from_url in USERS:
        st.session_state.auth = True
        st.session_state.user = user_from_url

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🏗️ БЕТОН ЗАВОД PRO</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            login = st.text_input("Логин")
            psw = st.text_input("Пароль", type="password")
            if st.button("Вход в систему"):
                if login in USERS and USERS[login] == psw:
                    st.session_state.update({"auth": True, "user": login})
                    st.query_params["logged_in"] = login
                    st.rerun()
                else: st.error("❌ Ошибка доступа")
    st.stop()

# ======================================================
# 3. БОКОВОЕ МЕНЮ
# ======================================================
with st.sidebar:
    st.title("⚙️ Управление")
    st.write(f"👤: **{st.session_state.user}**")
    cur_user = st.session_state.user

    if cur_user in ["director", "admin"]:
        st.divider()
        st.subheader("🏭 Заводы")
        new_plt = st.text_input("Новый завод", key="plt_input")
        if st.button("➕ Добавить завод"):
            if new_plt:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_plants (name) VALUES (?)", (new_plt.strip(),))
                    conn.commit()
                st.rerun()
        for p in get_list("ref_plants"):
            c_n, c_d = st.columns([4, 1])
            c_n.caption(p)
            if c_d.button("🗑️", key=f"del_p_{p}"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM ref_plants WHERE name = ?", (p,))
                    conn.commit()
                st.rerun()

    if cur_user in ["director", "buh", "admin"]:
        st.divider()
        st.subheader("🚚 Водители")
        new_drv = st.text_input("ФИО водителя", key="drv_input")
        if st.button("➕ Добавить водителя"):
            if new_drv:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv.strip(),))
                    conn.commit()
                st.rerun()
        for d in get_list("ref_drivers"):
            c_n, c_d = st.columns([4, 1])
            c_n.caption(d)
            if c_d.button("🗑️", key=f"del_d_{d}"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM ref_drivers WHERE name = ?", (d,))
                    conn.commit()
                st.rerun()

    if cur_user in ["director", "admin"]:
        st.divider()
        st.subheader("💎 Марки")
        new_grd = st.text_input("Новая марка", key="grd_input")
        if st.button("➕ Добавить марку"):
            if new_grd:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_grd.strip(),))
                    conn.commit()
                st.rerun()
        for g in get_list("ref_grades"):
            c_n, c_d = st.columns([4, 1])
            c_n.caption(g)
            if c_d.button("🗑️", key=f"del_g_{g}"):
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM ref_grades WHERE name = ?", (g,))
                    conn.commit()
                st.rerun()

    st.divider()
    if st.button("🚪 Выйти"):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

# ======================================================
# 4. ГЛАВНЫЙ ИНТЕРФЕЙС
# ======================================================
DRIVERS_LIST = get_list("ref_drivers")
GRADES_LIST = get_list("ref_grades")
PLANTS_LIST = get_list("ref_plants")

t1, t2, t3, t4 = st.tabs(["📝 Отгрузка", "📖 Журнал", "🏗️ Сводка по объектам", "📈 Аналитика"])

# --- ВКЛАДКА 1: ОТГРУЗКА ---
with t1:
    st.subheader("Новая накладная")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        plant_sel = c1.selectbox("🏭 Завод погрузки", PLANTS_LIST if PLANTS_LIST else ["Добавьте заводы"])
        obj_in = c2.text_input("📍 Объект (стройплощадка)")
        grade_sel = c3.selectbox("💎 Марка бетона", GRADES_LIST if GRADES_LIST else ["Добавьте марки"])
        drvs_sel = st.multiselect("🚛 Выберите водителей", DRIVERS_LIST)

    if drvs_sel and PLANTS_LIST and GRADES_LIST:
        f1, f2 = st.columns(2)
        p_val = f1.number_input("Цена за м³", min_value=0, step=100, value=0, format="%d")
        prep_val = f2.number_input("Общая предоплата", min_value=0, step=500, value=0, format="%d")

        entries = []
        wa_msg = f"🏗️ *БЕТОН-ЗАВОД*\n🏭 *Завод:* {plant_sel}\n📍 *Объект:* {obj_in}\n💎 *Марка:* {grade_sel}\n────────────────\n"
        
        for d in drvs_sel:
            with st.container(border=True):
                ca, cb, cc = st.columns([1, 1, 2])
                v = ca.number_input(f"м³ ({d})", min_value=0.0, max_value=100.0, step=0.1, value=0.0, key=f"v_{d}", format="%g")
                i = cb.text_input(f"Накл. №", key=f"i_{d}")
                if v > 0:
                    total_r = v * p_val
                    paid_r = prep_val / len(drvs_sel) if (prep_val > 0 and len(drvs_sel) > 0) else 0
                    entries.append([date.today().isoformat(), datetime.now().strftime("%H:%M"), plant_sel, obj_in, grade_sel, d, v, p_val, total_r, paid_r, (total_r - paid_r), i])
                    wa_msg += f"🚛 {d}: *{v} м³* (№{i})\n"

        if st.button("💾 СОХРАНИТЬ В БАЗУ", type="primary"):
            if obj_in and entries:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("INSERT INTO shipments (dt,tm,plant,object,grade,driver,volume,price_m3,total,paid,debt,invoice) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                    conn.commit()
                st.session_state.last_wa_text = wa_msg
                st.success("✅ Сохранено!")
                st.rerun()
            else: st.warning("Заполните объект и объем")

        if "last_wa_text" in st.session_state:
            enc_text = urllib.parse.quote(st.session_state.last_wa_text)
            st.markdown(f'<a href="https://wa.me/?text={enc_text}" target="_blank" class="wa-button">📲 ОТПРАВИТЬ В WHATSAPP</a>', unsafe_allow_html=True)
            if st.button("Очистить форму"):
                del st.session_state.last_wa_text
                st.rerun()

# --- ВКЛАДКА 2: ЖУРНАЛ ---
with t2:
    st.subheader("📖 Журнал отгрузок")
    fc1, fc2, fc3 = st.columns(3)
    d_range = fc1.date_input("Период", [date.today(), date.today()])
    f_plt = fc2.selectbox("Фильтр: Завод", ["Все"] + PLANTS_LIST)
    f_drv = fc3.selectbox("Фильтр: Водитель", ["Все"] + DRIVERS_LIST)
    
    with sqlite3.connect(DB_NAME) as conn:
        query = "SELECT * FROM shipments WHERE 1=1"
        params = []
        if isinstance(d_range, (list, tuple)) and len(d_range) == 2:
            query += " AND dt BETWEEN ? AND ?"
            params.extend([str(d_range[0]), str(d_range[1])])
        df = pd.read_sql(query, conn, params=params)

    if not df.empty:
        if f_plt != "Все": df = df[df['plant'] == f_plt]
        if f_drv != "Все": df = df[df['driver'] == f_drv]
        
        st.dataframe(df.drop(columns=['msg'], errors='ignore'), use_container_width=True, hide_index=True)
        
        df_ex = df.drop(columns=['id', 'msg'], errors='ignore').copy()
        df_ex.columns = ['Дата', 'Время', 'Завод', 'Объект', 'Марка', 'Водитель', 'Объем (м³)', 'Цена', 'Сумма', 'Оплачено', 'Долг', 'Накладная']
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_ex.to_excel(writer, index=False, sheet_name='Отгрузки')
        st.download_button("📥 СКАЧАТЬ EXCEL", buf.getvalue(), f"report_{date.today()}.xlsx")
        
        if cur_user in ["director", "admin"]:
            with st.expander("🛠️ Удалить запись"):
                e_id = st.number_input("Введите ID записи", min_value=0, step=1, format="%d")
                if st.button("🗑️ Удалить из базы"):
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.execute("DELETE FROM shipments WHERE id=?", (e_id,))
                        conn.commit()
                    st.rerun()

# --- ВКЛАДКА 3: СВОДКА ---
with t3:
    st.subheader("🏗️ Состояние по объектам")
    with sqlite3.connect(DB_NAME) as conn:
        df_obj = pd.read_sql("SELECT object, SUM(volume) as v, SUM(total) as t, SUM(paid) as p, SUM(debt) as d FROM shipments GROUP BY object", conn)
    
    if not df_obj.empty:
        for _, r in df_obj.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"#### 📍 {r['object']}")
                c2.metric("Объем", f"{r['v']:.1f} м³")
                c3.metric("Долг", f"{int(r['d']):,}")
                prog = min(r['p']/r['t'], 1.0) if r['t'] > 0 else 0
                st.progress(prog, text=f"Оплачено: {prog:.1%}")
    else: st.info("Данных пока нет")

# --- ВКЛАДКА 4: АНАЛИТИКА ---
with t4:
    st.subheader("📈 Аналитика")
    with sqlite3.connect(DB_NAME) as conn:
        df_an = pd.read_sql("SELECT dt, volume, total FROM shipments", conn)
    
    if not df_an.empty:
        df_an['dt'] = pd.to_datetime(df_an['dt'])
        
        c_an1, c_an2 = st.columns(2)
        with c_an1:
            st.write("**Динамика объема (м³)**")
            vol_chart = df_an.groupby('dt')['volume'].sum()
            st.area_chart(vol_chart)
        
        with c_an2:
            st.write("**Выручка по датам (₸/₽)**")
            cash_chart = df_an.groupby('dt')['total'].sum()
            st.bar_chart(cash_chart)
    else: st.info("Добавьте первую отгрузку для графиков")
