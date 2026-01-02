import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
import hashlib
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ И БЕЗОПАСНОСТЬ
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide")
DB_NAME = "database.db"

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# Пароли (Логин: Пароль)
USERS = {
    "director": {"hash": hash_password("1234"), "role": "director"},
    "buh": {"hash": hash_password("1111"), "role": "accountant"},
    "oper": {"hash": hash_password("2222"), "role": "operator"},
}

# ======================================================
# 2. РАБОТА С БАЗОЙ ДАННЫХ
# ======================================================
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT, msg TEXT
        )""")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_drivers (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_grades (name TEXT UNIQUE)")

def get_list(table):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            # Сортировка по алфавиту и порядку
            res = conn.execute(f"SELECT name FROM {table} ORDER BY name ASC").fetchall()
            return [r[0] for r in res]
    except:
        return []

def delete_item(table, name):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(f"DELETE FROM {table} WHERE name = ?", (name,))
    st.rerun()

init_db()

# ======================================================
# 3. АВТОРИЗАЦИЯ (С ЗАЩИТОЙ ОТ ОБНОВЛЕНИЯ СТРАНИЦЫ)
# ======================================================
if "auth" not in st.session_state:
    st.session_state.auth = False

# Если страница обновилась, проверяем логин в адресной строке
if not st.session_state.auth:
    query_params = st.query_params
    saved_user = query_params.get("logged_user")
    if saved_user in USERS:
        st.session_state.update({
            "auth": True, 
            "user": saved_user, 
            "role": USERS[saved_user]["role"]
        })

if not st.session_state.auth:
    st.title("🔐 Вход")
    login = st.text_input("Логин")
    psw = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if login in USERS and USERS[login]["hash"] == hash_password(psw):
            st.session_state.update({"auth": True, "user": login, "role": USERS[login]["role"]})
            st.query_params["logged_user"] = login
            st.rerun()
        else:
            st.error("Ошибка входа")
    st.stop()

# ======================================================
# 4. БОКОВОЕ МЕНЮ (НАСТРОЙКИ С ОЧИСТКОЙ И УДАЛЕНИЕМ)
# ======================================================
st.sidebar.header(f"👤 {st.session_state.user}")

if st.session_state.role == "director":
    with st.sidebar.expander("⚙️ НАСТРОЙКИ ЗАВОДА"):
        
        # --- ВОДИТЕЛИ ---
        st.subheader("Водители")
        if "drv_key" not in st.session_state: st.session_state.drv_key = 0
        
        new_drv = st.text_input("Имя водителя", key=f"drv_input_{st.session_state.drv_key}")
        if st.button("➕ Добавить"):
            if new_drv:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv.strip(),))
                st.session_state.drv_key += 1 # Меняем ключ для очистки поля
                st.rerun()

        for d in get_list("ref_drivers"):
            col1, col2 = st.columns([4, 1])
            col1.write(d)
            with col2.popover("🗑"):
                if st.button("Удалить", key=f"del_d_{d}"):
                    delete_item("ref_drivers", d)

        st.divider()

        # --- МАРКИ БЕТОНА ---
        st.subheader("Марки")
        if "grd_key" not in st.session_state: st.session_state.grd_key = 0
        
        new_grd = st.text_input("Новая марка", key=f"grd_input_{st.session_state.grd_key}")
        if st.button("➕ Добавить марку"):
            if new_grd:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_grd.strip(),))
                st.session_state.grd_key += 1
                st.rerun()

        for g in get_list("ref_grades"):
            col1, col2 = st.columns([4, 1])
            col1.write(g)
            with col2.popover("🗑"):
                if st.button("Удалить", key=f"del_g_{g}"):
                    delete_item("ref_grades", g)

if st.sidebar.button("🚪 Выйти"):
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

DRIVERS_LIST = get_list("ref_drivers")
GRADES_LIST = get_list("ref_grades")

# ======================================================
# 5. ОСНОВНОЙ ИНТЕРФЕЙС
# ======================================================
t1, t2, t3, t4 = st.tabs(["📝 Отгрузка", "📊 Отчёты", "📈 Графики", "🚛 Статистика"])

# --- ВКЛАДКА: ОТГРУЗКА ---
with t1:
    if not DRIVERS_LIST or not GRADES_LIST:
        st.info("💡 Откройте меню слева и добавьте данные в настройках.")
    else:
        st.subheader("Новая запись")
        obj = st.text_input("📍 Объект")
        c1, c2 = st.columns(2)
        grade = c1.selectbox("💎 Марка", GRADES_LIST)
        selected = c2.multiselect("🚛 Водители", DRIVERS_LIST)

        price, paid_total = 0.0, 0.0
        if st.session_state.role in ["accountant", "director"]:
            f1, f2 = st.columns(2)
            price = f1.number_input("Цена за м³", min_value=0.0, step=100.0)
            paid_total = f2.number_input("Оплачено всего", min_value=0.0, step=500.0)

        entries = []
        wa_text = f"🏗 *ОТГРУЗКА БЕТОНА*\n📍 Объект: {obj}\n💎 Марка: {grade}\n────────────\n"

        for d in selected:
            sc1, sc2, sc3 = st.columns([2, 1, 1])
            sc1.write(f"**{d}**")
            vol = sc2.number_input("м³", 0.0, step=0.5, key=f"v_{d}")
            inv = sc3.text_input("№ Накл.", key=f"i_{d}")
            if vol > 0:
                total = vol * price
                share_paid = paid_total / len(selected) if paid_total > 0 else 0
                debt = total - share_paid
                now = datetime.now()
                entries.append([
                    now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                    obj, grade, d, vol, price, total, share_paid, debt, inv, ""
                ])
                wa_text += f"🚛 {d}: *{vol} м³* (№{inv})\n"

        if st.button("💾 СОХРАНИТЬ В БАЗУ", use_container_width=True):
            if not obj or not entries:
                st.warning("Заполните данные")
            else:
                for e in entries: e[11] = wa_text
                with sqlite3.connect(DB_NAME) as conn:
                    conn.executemany("INSERT INTO shipments (dt,tm,object,grade,driver,volume,price_m3,total,paid,debt,invoice,msg) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                st.success("Данные успешно сохранены!")
                st.session_state.last_wa = wa_text
                st.rerun() # Чтобы закрыть шторки и очистить форму

        if "last_wa" in st.session_state:
            wa_url = f"https://wa.me/?text={urllib.parse.quote(st.session_state.last_wa)}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25D366; color:white; border:none; padding:12px; border-radius:8px; width:100%; cursor:pointer; font-weight:bold;">📲 ОТПРАВИТЬ В WHATSAPP</button></a>', unsafe_allow_html=True)

# --- ВКЛАДКА: ОТЧЕТЫ (УЛУЧШЕННЫЙ EXCEL) ---
with t2:
    st.subheader("Поиск и фильтры")
    fc1, fc2 = st.columns(2)
    f_date = fc1.date_input("Дата", date.today())
    f_drv = fc2.selectbox("Водитель", ["Все"] + DRIVERS_LIST)

    query = "SELECT dt as 'Дата', tm as 'Время', object as 'Объект', grade as 'Марка', driver as 'Водитель', volume as 'Объем', price_m3 as 'Цена', total as 'Сумма', paid as 'Оплачено', debt as 'Долг', invoice as 'Накладная' FROM shipments WHERE dt = ?"
    params = [str(f_date)]
    if f_drv != "Все":
        query += " AND driver = ?"
        params.append(f_drv)

    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql(query, conn, params=params)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Отчет')
            worksheet = writer.sheets['Отчет']
            for i, col in enumerate(df.columns):
                width = max(df[col].astype(str).str.len().max(), len(col)) + 2
                worksheet.set_column(i, i, width)
        
        st.download_button(label="📥 СКАЧАТЬ EXCEL", data=buf.getvalue(), file_name=f"rep_{f_date}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Нет записей")

# --- ВКЛАДКА: ГРАФИКИ ---
with t3:
    with sqlite3.connect(DB_NAME) as conn:
        df_all = pd.read_sql("SELECT driver, volume FROM shipments", conn)
    if not df_all.empty:
        st.write("### Объем по водителям (м³)")
        st.bar_chart(df_all.groupby("driver")["volume"].sum())

# --- ВКЛАДКА: ВОДИТЕЛИ ---
with t4:
    with sqlite3.connect(DB_NAME) as conn:
        df_d = pd.read_sql("SELECT driver as 'Водитель', SUM(volume) as 'Всего м3', COUNT(id) as 'Рейсов' FROM shipments GROUP BY driver", conn)
    if not df_d.empty:
        st.table(df_d)
