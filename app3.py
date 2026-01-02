import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ И ДИЗАЙН
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide", page_icon="🏗️")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .metric-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #007bff; }
    </style>
    """, unsafe_allow_html=True)

DB_NAME = "database.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT, msg TEXT)""")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_drivers (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_grades (name TEXT UNIQUE)")
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
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>🏗️ БЕТОН ЗАВОД PRO</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            login = st.text_input("Логин")
            psw = st.text_input("Пароль", type="password")
            if st.button("Вход в систему"):
                if login == "admin" and psw == "1234": # Смените на свои
                    st.session_state.update({"auth": True, "user": login, "role": "director"})
                    st.rerun()
                else: st.error("Ошибка доступа")
    st.stop()

# ======================================================
# 3. БОКОВОЕ МЕНЮ (СПРАВОЧНИКИ)
# ======================================================
with st.sidebar:
    st.title("⚙️ Настройки")
    st.write(f"👤: **{st.session_state.user}**")
    
    with st.expander("🚚 Водители"):
        new_drv = st.text_input("ФИО водителя")
        if st.button("Добавить"):
            if new_drv:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv.strip(),))
                    conn.commit()
                st.rerun()
        for d in get_list("ref_drivers"):
            st.caption(f"• {d}")

    with st.expander("💎 Марки бетона"):
        new_grd = st.text_input("Название марки")
        if st.button("Сохранить марку"):
            if new_grd:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_grd.strip(),))
                    conn.commit()
                st.rerun()

    st.divider()
    with open(DB_NAME, "rb") as f:
        st.download_button("📥 Резервная копия базы (DB)", f, file_name=f"base_{date.today()}.db")
    
    if st.button("🚪 Выход"):
        st.session_state.clear()
        st.rerun()

# ======================================================
# 4. ГЛАВНЫЙ ИНТЕРФЕЙС
# ======================================================
DRIVERS_LIST = get_list("ref_drivers")
GRADES_LIST = get_list("ref_grades")

t1, t2, t3, t4 = st.tabs(["📝 Отгрузка", "📊 Журнал", "🏗️ Сводка по объектам", "📈 Аналитика"])

# --- ВКЛАДКА 1: НОВАЯ ОТГРУЗКА ---
with t1:
    st.subheader("Формирование новой накладной")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        obj_name = c1.text_input("📍 Объект", placeholder="Куда везем?")
        grade_name = c2.selectbox("💎 Марка", GRADES_LIST)
        selected_drvs = st.multiselect("🚛 Выберите водителей", DRIVERS_LIST)

    if selected_drvs:
        st.write("### Детали машин")
        f1, f2 = st.columns(2)
        price_val = f1.number_input("Цена за м³", min_value=0.0, step=100.0, value=2500.0)
        prepaid = f2.number_input("Общая предоплата на этот выезд", min_value=0.0)

        shipment_entries = []
        for d in selected_drvs:
            with st.container(border=True):
                col_a, col_b, col_c = st.columns([1, 1, 2])
                v = col_a.number_input(f"м³ ({d})", 0.0, 50.0, step=0.5, key=f"v_{d}")
                i = col_b.text_input(f"Накладная", key=f"i_{d}")
                if v > 0:
                    total_r = v * price_val
                    paid_r = prepaid / len(selected_drvs) if prepaid > 0 else 0
                    shipment_entries.append([
                        date.today().isoformat(), datetime.now().strftime("%H:%M"),
                        obj_name, grade_name, d, v, price_val, total_r, paid_r, (total_r - paid_r), i
                    ])

        if st.button("💾 СОХРАНИТЬ В БАЗУ", type="primary"):
            if not obj_name or not shipment_entries:
                st.error("Заполните объект и объем!")
            else:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("""INSERT INTO shipments 
                        (dt, tm, object, grade, driver, volume, price_m3, total, paid, debt, invoice) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""", shipment_entries)
                    conn.commit()
                st.success("Данные сохранены!")
                st.balloons()
                st.rerun()

# --- ВКЛАДКА 2: ЖУРНАЛ + РЕДАКТИРОВАНИЕ ---
with t2:
    st.subheader("📖 Журнал всех отгрузок")
    
    # Фильтры
    fc1, fc2, fc3 = st.columns([2, 2, 1])
    d_range = fc1.date_input("Период", [date.today(), date.today()])
    f_drv = fc2.selectbox("Водитель", ["Все"] + DRIVERS_LIST)
    
    with sqlite3.connect(DB_NAME) as conn:
        q = "SELECT * FROM shipments WHERE 1=1"
        p = []
        if len(d_range) == 2:
            q += " AND dt BETWEEN ? AND ?"
            p.extend([str(d_range[0]), str(d_range[1])])
        df_journal = pd.read_sql(q, conn, params=p)

    if not df_journal.empty:
        if f_drv != "Все": df_journal = df_journal[df_journal['driver'] == f_drv]
        
        st.dataframe(df_journal.drop(columns=['msg'], errors='ignore'), use_container_width=True, hide_index=True)
        
        # Редактирование
        with st.expander("🛠️ Редактировать / Удалить по ID"):
            edit_id = st.number_input("ID записи", min_value=0, step=1)
            if edit_id > 0:
                row = df_journal[df_journal['id'] == edit_id]
                if not row.empty:
                    ec1, ec2, ec3 = st.columns(3)
                    new_v = ec1.number_input("Объем", value=float(row['volume'].values[0]))
                    new_p = ec2.number_input("Оплачено", value=float(row['paid'].values[0]))
                    new_i = ec3.text_input("Накладная", value=str(row['invoice'].values[0]))
                    
                    b_save, b_del = st.columns(2)
                    if b_save.button("💾 Применить правки"):
                        new_t = new_v * float(row['price_m3'].values[0])
                        with sqlite3.connect(DB_NAME) as conn:
                            conn.execute("UPDATE shipments SET volume=?, paid=?, invoice=?, total=?, debt=? WHERE id=?", 
                                         (new_v, new_p, new_i, new_t, (new_t-new_p), edit_id))
                            conn.commit()
                        st.rerun()
                    if b_del.button("🗑️ Удалить запись"):
                        with sqlite3.connect(DB_NAME) as conn:
                            conn.execute("DELETE FROM shipments WHERE id=?", (edit_id,))
                            conn.commit()
                        st.rerun()
    else: st.info("Нет записей")

# --- ВКЛАДКА 3: СВОДКА ПО ОБЪЕКТАМ ---
with t4:
    st.subheader("🏗️ Состояние по объектам")
    with sqlite3.connect(DB_NAME) as conn:
        df_obj = pd.read_sql("""SELECT object, SUM(volume) as v, SUM(total) as t, SUM(paid) as p, SUM(debt) as d 
                                FROM shipments GROUP BY object""", conn)
    
    if not df_obj.empty:
        for _, r in df_obj.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"#### 📍 {r['object']}")
                c2.metric("Объем", f"{r['v']} м³")
                c3.metric("Долг", f"{r['d']:,.0f}")
                progress = min(r['p']/r['t'], 1.0) if r['t'] > 0 else 0
                st.progress(progress, text=f"Оплачено {progress:.1%}")
    else: st.info("Нет данных")

# --- ВКЛАДКА 4: АНАЛИТИКА ---
with t3:
    st.subheader("📈 Аналитика")
    if not df_journal.empty:
        st.bar_chart(df_journal.groupby("driver")["volume"].sum())
        st.area_chart(df_journal.groupby("dt")["volume"].sum())
