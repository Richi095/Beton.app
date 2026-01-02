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

# Хэшированные пароли для входа
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
        # Таблица отгрузок
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT, tm TEXT, object TEXT, grade TEXT, 
            driver TEXT, volume REAL, price_m3 REAL, 
            total REAL, paid REAL, debt REAL, invoice TEXT, msg TEXT
        )""")
        # Справочники
        conn.execute("CREATE TABLE IF NOT EXISTS ref_drivers (name TEXT UNIQUE)")
        conn.execute("CREATE TABLE IF NOT EXISTS ref_grades (name TEXT UNIQUE)")

def get_list(table):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            res = conn.execute(f"SELECT name FROM {table}").fetchall()
            return [r[0] for r in res]
    except:
        return []

init_db()

# ======================================================
# 3. СИСТЕМА АВТОРИЗАЦИИ
# ======================================================
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Вход в систему")
    login = st.text_input("Логин")
    psw = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if login in USERS and USERS[login]["hash"] == hash_password(psw):
            st.session_state.update({"auth": True, "user": login, "role": USERS[login]["role"]})
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

# ======================================================
# 4. БОКОВАЯ ПАНЕЛЬ (НАСТРОЙКИ И ВЫХОД)
# ======================================================
st.sidebar.header(f"👤 {st.session_state.user}")

# Управление справочниками доступно только Директору в боковом меню
if st.session_state.role == "director":
    with st.sidebar.expander("⚙️ НАСТРОЙКИ ЗАВОДА"):
        st.subheader("Водители")
        new_drv = st.text_input("Имя водителя")
        if st.button("➕ Добавить водителя"):
            if new_drv:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_drivers (name) VALUES (?)", (new_drv,))
                st.rerun()
        
        st.divider()
        
        st.subheader("Марки бетона")
        new_grd = st.text_input("Марка (напр. М300)")
        if st.button("➕ Добавить марку"):
            if new_grd:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("INSERT OR IGNORE INTO ref_grades (name) VALUES (?)", (new_grd,))
                st.rerun()
        
        st.divider()
        if st.button("📥 Бэкап базы (.db)"):
            with open(DB_NAME, "rb") as f:
                st.download_button("Скачать файл БД", f, file_name="beton_backup.db")

if st.sidebar.button("🚪 Выйти из системы"):
    st.session_state.clear()
    st.rerun()

# Загружаем актуальные списки
DRIVERS_LIST = get_list("ref_drivers")
GRADES_LIST = get_list("ref_grades")

# ======================================================
# 5. ОСНОВНЫЕ ВКЛАДКИ
# ======================================================
t1, t2, t3, t4 = st.tabs(["📝 Отгрузка", "📊 Отчёты", "📈 Графики", "🚛 Водители"])

# --- ВКЛАДКА: ОТГРУЗКА ---
with t1:
    if not DRIVERS_LIST or not GRADES_LIST:
        st.info("👋 Добро пожаловать! Откройте меню слева (⚙️ Настройки) и добавьте первых водителей и марки бетона.")
    else:
        st.subheader("Новая отгрузка")
        obj = st.text_input("📍 Объект / Заказчик")
        c1, c2 = st.columns(2)
        grade = c1.selectbox("💎 Марка", GRADES_LIST)
        selected_drivers = c2.multiselect("🚛 Выбрать водителей", DRIVERS_LIST)

        price, paid_total = 0.0, 0.0
        if st.session_state.role in ["accountant", "director"]:
            f1, f2 = st.columns(2)
            price = f1.number_input("Цена за м³", min_value=0.0, step=100.0)
            paid_total = f2.number_input("Оплачено (всего)", min_value=0.0, step=500.0)

        entries = []
        wa_text = f"🏗 *ОТГРУЗКА БЕТОНА*\n📍 Объект: {obj}\n💎 Марка: {grade}\n────────────\n"

        if selected_drivers:
            for d in selected_drivers:
                sc1, sc2, sc3 = st.columns([2, 1, 1])
                sc1.markdown(f"**{d}**")
                vol = sc2.number_input(f"м³", 0.0, step=0.5, key=f"v_{d}")
                inv = sc3.text_input(f"№ Накл.", key=f"i_{d}")
                
                if vol > 0:
                    total = vol * price
                    # Распределяем общую оплату пропорционально (упрощенно)
                    share_paid = paid_total / len(selected_drivers) if paid_total > 0 else 0
                    debt = total - share_paid
                    now = datetime.now()
                    entries.append([
                        now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                        obj, grade, d, vol, price, total, share_paid, debt, inv, ""
                    ])
                    wa_text += f"🚛 {d}: *{vol} м³* (№{inv})\n"

            if st.button("💾 СОХРАНИТЬ В БАЗУ", use_container_width=True):
                if not obj or not entries:
                    st.error("Заполните объект и объем")
                else:
                    for e in entries: e[11] = wa_text
                    with sqlite3.connect(DB_NAME) as conn:
                        conn.executemany("INSERT INTO shipments (dt, tm, object, grade, driver, volume, price_m3, total, paid, debt, invoice, msg) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", entries)
                    st.success("Данные успешно сохранены!")
                    st.session_state.last_wa = wa_text

            if "last_wa" in st.session_state:
                wa_url = f"https://wa.me/?text={urllib.parse.quote(st.session_state.last_wa)}"
                st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25D366; color:white; border:none; padding:12px; border-radius:8px; width:100%; cursor:pointer; font-weight:bold;">📲 ОТПРАВИТЬ В WHATSAPP</button></a>', unsafe_allow_html=True)

# --- ВКЛАДКА: ОТЧЕТЫ (С ФИЛЬТРАМИ) ---
with t2:
    st.subheader("Просмотр отчетов")
    fc1, fc2 = st.columns(2)
    f_date = fc1.date_input("Дата", date.today())
    f_drv = fc2.selectbox("Фильтр по водителю", ["Все"] + DRIVERS_LIST)

    query = "SELECT dt as 'Дата', tm as 'Время', object as 'Объект', grade as 'Марка', driver as 'Водитель', volume as 'Объем', price_m3 as 'Цена', total as 'Сумма', paid as 'Оплачено', debt as 'Долг', invoice as 'Накладная' FROM shipments WHERE dt = ?"
    params = [str(f_date)]
    if f_drv != "Все":
        query += " AND driver = ?"
        params.append(f_drv)

    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql(query, conn, params=params)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        # Итоги дня
        mc1, mc2 = st.columns(2)
        mc1.metric("Всего объем", f"{df['Объем'].sum()} м³")
        mc2.metric("Общий долг", f"{df['Долг'].sum():,.0f} руб.")
        
        # Excel экспорт
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Отчет')
        st.download_button("📥 СКАЧАТЬ EXCEL", buf.getvalue(), f"report_{f_date}.xlsx", "application/vnd.ms-excel")
    else:
        st.info("За эту дату записей нет")

# --- ВКЛАДКА: ГРАФИКИ ---
with t3:
    with sqlite3.connect(DB_NAME) as conn:
        df_all = pd.read_sql("SELECT driver, volume, object FROM shipments", conn)
    if not df_all.empty:
        st.write("### Объем по водителям (м³)")
        st.bar_chart(df_all.groupby("driver")["volume"].sum())
        st.write("### Объем по объектам (м³)")
        st.bar_chart(df_all.groupby("object")["volume"].sum())

# --- ВКЛАДКА: ВОДИТЕЛИ (СТАТИСТИКА) ---
with t4:
    with sqlite3.connect(DB_NAME) as conn:
        df_d = pd.read_sql("SELECT driver as 'Водитель', SUM(volume) as 'Всего м3', COUNT(id) as 'Рейсов' FROM shipments GROUP BY driver", conn)
    if not df_d.empty:
        st.table(df_d)
    else:
        st.write("Нет данных")
