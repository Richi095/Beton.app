import streamlit as st
import pandas as pd
import sqlite3
import io
import urllib.parse
from datetime import datetime, date

# ======================================================
# 1. КОНФИГУРАЦИЯ И НАСТРОЙКИ
# ======================================================
st.set_page_config(page_title="Бетон Завод PRO", layout="wide")

DB_NAME = "database.db"

# Пользователи системы
USERS = {
    "director": {"password": "1234", "role": "director"},
    "buh": {"password": "1111", "role": "accountant"},
    "oper": {"password": "2222", "role": "operator"},
}

# Список водителей
DRIVERS = ["Иванов", "Соколов", "Андреев", "Петров", "Кузнецов", "Морозов"]

# ======================================================
# 2. РАБОТА С БАЗОЙ ДАННЫХ
# ======================================================
def init_db():
    """Создает таблицу при первом запуске"""
    with sqlite3.connect(DB_NAME) as conn:
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

def save_shipments_to_db(data_list):
    """Сохраняет пачку рейсов в базу"""
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.executemany("""
        INSERT INTO shipments 
        (dt, tm, object, grade, driver, volume, price_m3, total, paid, debt, invoice, msg)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, data_list)
        conn.commit()

init_db()

# ======================================================
# 3. СИСТЕМА АВТОРИЗАЦИИ
# ======================================================
if "auth" not in st.session_state:
    # Проверка параметров в URL для авто-входа
    q_params = st.query_params
    if "user" in q_params and q_params["user"] in USERS:
        u_key = q_params["user"]
        st.session_state.auth = True
        st.session_state.user = u_key
        st.session_state.role = USERS[u_key]["role"]
    else:
        st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Вход в систему")
    u = st.text_input("Логин")
    p = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        if u in USERS and USERS[u]["password"] == p:
            st.query_params["user"] = u
            st.session_state.auth = True
            st.session_state.user = u
            st.session_state.role = USERS[u]["role"]
            st.rerun()
        else:
            st.error("Неверный логин или пароль")
    st.stop()

# ======================================================
# 4. ГЛАВНЫЙ ИНТЕРФЕЙС
# ======================================================
st.sidebar.title("🏗 Завод Бетона")
st.sidebar.write(f"**Пользователь:** {st.session_state.user}")
st.sidebar.write(f"**Роль:** {st.session_state.role.upper()}")

if st.sidebar.button("🚪 Выйти"):
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

tabs = st.tabs(["📝 Отгрузка", "📊 Отчёты", "📈 Аналитика", "🚛 Водители"])

# --- ВКЛАДКА 1: ОТГРУЗКА ---
with tabs[0]:
    st.subheader("Формирование новой заявки")
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        obj_name = st.text_input("📍 Объект / Адрес")
        concrete_grade = st.selectbox("💎 Марка бетона", ["М200","М250","М300","М350","М400"])
    with col_h2:
        selected_drivers = st.multiselect("🚛 Выберите водителей (рейсы)", DRIVERS)

    # Поля цен доступны только бухгалтерии и директору
    price_val = 0.0
    paid_val = 0.0
    if st.session_state.role in ["accountant", "director"]:
        f_c1, f_c2 = st.columns(2)
        price_val = f_c1.number_input("Цена за м³ (₸)", min_value=0.0, step=500.0)
        paid_val = f_c2.number_input("Оплачено всего (₸)", min_value=0.0, step=1000.0)

    st.divider()
    
    shipments_data = []
    report_msg = f"🏗 *ОТГРУЗКА БЕТОНА*\n📍 *Объект:* {obj_name}\n💎 *Марка:* {concrete_grade}\n────────────\n"

    if selected_drivers:
        for driver in selected_drivers:
            r1, r2, r3 = st.columns([2, 1, 1])
            with r1: st.markdown(f"**{driver}**")
            with r2: v = st.number_input("м³", 0.0, step=0.5, key=f"v_{driver}")
            with r3: n = st.text_input("№ Накл.", key=f"n_{driver}")

            if v > 0:
                total_sum = v * price_val
                # Простейшее распределение долга для примера
                debt_val = total_sum - (paid_val / len(selected_drivers) if paid_val > 0 else 0)
                
                now = datetime.now()
                shipments_data.append((
                    now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
                    obj_name, concrete_grade, driver, v, price_val, total_sum, paid_val, debt_val, n, ""
                ))
                
                line = f"🚛 {driver}: *{v} м³*"
                if st.session_state.role in ["accountant", "director"]:
                    line += f" × {price_val} = *{total_sum}₸*"
                report_msg += line + f" (№{n})\n"

    if st.button("💾 Сохранить в базу"):
        if not obj_name or not shipments_data:
            st.error("Ошибка: Введите объект и данные хотя бы одного водителя!")
        else:
            # Вставляем текст сообщения в каждую запись
            final_list = [list(item) for item in shipments_data]
            for item in final_list: item[11] = report_msg
            
            save_shipments_to_db(final_list)
            st.success(f"Успешно сохранено рейсов: {len(shipments_data)}")
            st.session_state['last_msg'] = report_msg

    # Кнопка WhatsApp
    if 'last_msg' in st.session_state:
        st.info("Текст для отправки:")
        st.code(st.session_state['last_msg'])
        wa_encoded = urllib.parse.quote(st.session_state['last_msg'])
        st.markdown(f"""
            <a href="https://wa.me/?text={wa_encoded}" target="_blank">
            <button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:8px; font-weight:bold;">
            🟢 ОТПРАВИТЬ В WHATSAPP
            </button></a>
        """, unsafe_allow_html=True)

# --- ВКЛАДКА 2: ОТЧЕТЫ ---
with tabs[1]:
    filter_date = st.date_input("Показать данные за:", date.today())
    with sqlite3.connect(DB_NAME) as conn:
        df_report = pd.read_sql("SELECT * FROM shipments WHERE dt=?", conn, params=(str(filter_date),))
    
    if not df_report.empty:
        # СКАЧИВАНИЕ В EXCEL
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_report.to_excel(writer, index=False, sheet_name='Отгрузки')
        
        st.download_button(
            label="📥 Скачать этот отчёт в Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"beton_report_{filter_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Всего кубов", f"{df_report['volume'].sum():.1f} м³")
        m2.metric("Общая сумма", f"{df_report['total'].sum():,.0f} ₸")
        m3.metric("Общий долг", f"{df_report['debt'].sum():,.0f} ₸")
        
        st.dataframe(df_report, use_container_width=True)
    else:
        st.warning("За указанную дату записей не найдено.")

# --- ВКЛАДКА 3: АНАЛИТИКА ---
with tabs[2]:
    with sqlite3.connect(DB_NAME) as conn:
        df_all = pd.read_sql("SELECT * FROM shipments", conn)
    
    if not df_all.empty:
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.write("### Популярность марок бетона")
            st.bar_chart(df_all.groupby("grade")["volume"].sum())
        with col_ch2:
            st.write("### Объем по водителям (м³)")
            st.bar_chart(df_all.groupby("driver")["volume"].sum())
    else:
        st.info("Нет данных для анализа.")

# --- ВКЛАДКА 4: ВОДИТЕЛИ ---
with tabs[3]:
    with sqlite3.connect(DB_NAME) as conn:
        # Сводная таблица по всем водителям
        df_drivers = pd.read_sql("""
            SELECT driver AS "Водитель", 
                   SUM(volume) AS "Всего доставлено (м³)", 
                   COUNT(id) AS "Количество рейсов"
            FROM shipments GROUP BY driver
        """, conn)
    st.dataframe(df_drivers, use_container_width=True)
