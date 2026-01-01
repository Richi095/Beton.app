import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os

st.set_page_config(page_title="Бетон Завод (Умный выбор)", layout="wide")

# ====== НАСТРОЙКИ ======
EXCEL_FILE = "otgruzka.xlsx"

ALL_DRIVERS = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов", "Дмитрий Кузнецов",
    "Андрей Попов", "Михаил Новиков", "Артем Морозов", "Игорь Волков",
    "Виктор Васильев", "Николай Федоров"
]

# ====== ЗАГРУЗКА ДАННЫХ ======
if 'db' not in st.session_state:
    if os.path.exists(EXCEL_FILE):
        st.session_state.db = pd.read_excel(EXCEL_FILE).to_dict("records")
    else:
        st.session_state.db = []

st.title("🏗 Управление отгрузкой бетона")

tab1, tab2, tab3 = st.tabs(["📝 Бухгалтерия", "🧱 Оператор", "🚛 Водители"])

# ======================================================
# 📝 БУХГАЛТЕРИЯ
# ======================================================
with tab1:
    st.subheader("Формирование нового рейса")

    col_a, col_b = st.columns(2)
    with col_a:
        obj = st.text_input("📍 Объект", placeholder="Куда везем?")
    with col_b:
        grade = st.selectbox("💎 Марка бетона", ["М100","М150","М200","М250","М300","М350","М400"])

    selected_drivers = st.multiselect("👥 Выберите водителей:", ALL_DRIVERS)

    st.divider()

    batch_entries = []
    total_volume = 0

    if selected_drivers:
        st.markdown("### 🚛 Данные по машинам")
        for i, name in enumerate(selected_drivers):
            c1, c2, c3 = st.columns([2,1,1])
            with c1:
                st.markdown(f"**{name}**")
            with c2:
                v = st.number_input(
                    "Кубы",
                    min_value=0.0,
                    step=0.5,
                    key=f"vol_{i}"
                )
            with c3:
                n = st.text_input(
                    "Накладная №",
                    key=f"inv_{i}"
                )

            batch_entries.append({
                "name": name,
                "vol": v,
                "inv": n
            })
            total_volume += v
    else:
        st.info("⬆ Выберите водителей для ввода данных")

    st.metric("🚚 Общий объем рейса", f"{total_volume} м³")

    # ===== СОХРАНЕНИЕ =====
    if st.button("💾 СОХРАНИТЬ И СФОРМИРОВАТЬ СПИСОК"):
        if not obj:
            st.error("Введите объект!")
            st.stop()

        if total_volume == 0:
            st.warning("Общий объем равен 0 м³")
            st.stop()

        report_msg = (
            f"🏗 *ОТГРУЗКА БЕТОНА* 🏗\n"
            f"📍 *Объект:* {obj}\n"
            f"💎 *Марка:* {grade}\n"
            f"--------------------------\n"
        )

        saved = 0
        for item in batch_entries:
            if item["vol"] > 0 and item["inv"]:
                entry = {
                    "Дата": datetime.now().strftime("%d.%m.%Y"),
                    "Время": datetime.now().strftime("%H:%M"),
                    "Объект": obj,
                    "Марка": grade,
                    "Объем": item["vol"],
                    "Водитель": item["name"],
                    "Накладная": item["inv"]
                }
                st.session_state.db.append(entry)
                report_msg += f"🚛 {item['name']} — *{item['vol']} м³* (№{item['inv']})\n"
                saved += 1

        if saved == 0:
            st.error("Нет заполненных рейсов (объем + накладная)")
            st.stop()

        report_msg += "--------------------------\n✅ *Всем удачного рейса!*"
        st.session_state.group_msg = report_msg

        # СОХРАНЕНИЕ В EXCEL
        df = pd.DataFrame(st.session_state.db)
        df.to_excel(EXCEL_FILE, index=False)

        st.success(f"✅ Сохранено рейсов: {saved}")

    # ===== WHATSAPP =====
    if "group_msg" in st.session_state:
        st.divider()
        st.subheader("📲 Отправка в WhatsApp")
        st.code(st.session_state.group_msg)

        encoded = urllib.parse.quote(st.session_state.group_msg)
        wa_url = f"https://wa.me/?text={encoded}"

        st.markdown(f"""
        <a href="{wa_url}" target="_blank">
            <button style="
                width:100%;
                background:#25D366;
                color:white;
                border:none;
                padding:15px;
                font-size:16px;
                border-radius:10px;
                font-weight:bold;">
                🟢 ОТПРАВИТЬ В WHATSAPP
            </button>
        </a>
        """, unsafe_allow_html=True)

        # СКАЧИВАНИЕ EXCEL
        with open(EXCEL_FILE, "rb") as f:
            st.download_button(
                "📥 Скачать Excel",
                data=f,
                file_name=EXCEL_FILE
            )

# ======================================================
# 🧱 ОПЕРАТОР
# ======================================================
with tab2:
    st.subheader("Последние отгрузки")
    if st.session_state.db:
        df = pd.DataFrame(st.session_state.db)
        st.dataframe(df.tail(20), use_container_width=True)
    else:
        st.info("Нет данных")

# ======================================================
# 🚛 ВОДИТЕЛИ
# ======================================================
with tab3:
    st.subheader("Лента рейсов")
    if st.session_state.db:
        for item in reversed(st.session_state.db[-20:]):
            st.success(
                f"{item['Дата']} {item['Время']} | "
                f"{item['Водитель']} | "
                f"{item['Объем']} м³ | "
                f"{item['Объект']}"
            )
    else:
        st.info("Пока пусто")
