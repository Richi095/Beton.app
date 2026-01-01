import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os

# ======================================================
# НАСТРОЙКИ
# ======================================================
st.set_page_config(
    page_title="Бетон Завод — Отгрузка",
    layout="wide"
)

ALL_DRIVERS = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов",
    "Дмитрий Кузнецов", "Андрей Попов", "Михаил Новиков",
    "Артем Морозов", "Игорь Волков",
    "Виктор Васильев", "Николай Федоров"
]

# ======================================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ
# ======================================================
if "db" not in st.session_state:
    st.session_state.db = []

if "last_file" not in st.session_state:
    st.session_state.last_file = None

# ======================================================
# ИНТЕРФЕЙС
# ======================================================
st.title("🏗 Управление отгрузкой бетона")

tab1, tab2, tab3 = st.tabs([
    "📝 Бухгалтерия",
    "🧱 Оператор",
    "🚛 Водители"
])

# ======================================================
# 📝 БУХГАЛТЕРИЯ
# ======================================================
with tab1:
    st.subheader("Формирование рейса")

    c1, c2 = st.columns(2)
    with c1:
        obj = st.text_input("📍 Объект")
    with c2:
        grade = st.selectbox(
            "💎 Марка бетона",
            ["М100","М150","М200","М250","М300","М350","М400"]
        )

    selected_drivers = st.multiselect(
        "👥 Выберите водителей",
        ALL_DRIVERS
    )

    st.divider()

    batch = []
    total_volume = 0.0

    if selected_drivers:
        st.markdown("### 🚛 Данные по машинам")
        for i, name in enumerate(selected_drivers):
            col1, col2, col3 = st.columns([2,1,1])
            with col1:
                st.markdown(f"**{name}**")
            with col2:
                vol = st.number_input(
                    "Кубы",
                    min_value=0.0,
                    step=0.5,
                    key=f"vol_{i}"
                )
            with col3:
                inv = st.text_input(
                    "Накладная №",
                    key=f"inv_{i}"
                )

            batch.append({
                "name": name,
                "vol": vol,
                "inv": inv
            })
            total_volume += vol
    else:
        st.info("Выберите водителей для ввода")

    st.metric("🚚 Общий объем рейса", f"{total_volume} м³")

    # ==================================================
    # СОХРАНЕНИЕ + АВТО-ФОРМАТ
    # ==================================================
    if st.button("💾 СОХРАНИТЬ И СФОРМИРОВАТЬ СПИСОК"):
        if not obj:
            st.error("Введите объект")
            st.stop()

        if total_volume == 0:
            st.warning("Общий объем 0 м³")
            st.stop()

        msg = (
            f"🏗 *ОТГРУЗКА БЕТОНА* 🏗\n"
            f"📍 *Объект:* {obj}\n"
            f"💎 *Марка:* {grade}\n"
            f"--------------------------\n"
        )

        saved = 0
        for item in batch:
            if item["vol"] > 0 and item["inv"]:
                record = {
                    "Дата": datetime.now().strftime("%d.%m.%Y"),
                    "Время": datetime.now().strftime("%H:%M"),
                    "Объект": obj,
                    "Марка": grade,
                    "Водитель": item["name"],
                    "Объем": item["vol"],
                    "Накладная": item["inv"]
                }
                st.session_state.db.append(record)

                msg += (
                    f"🚛 {item['name']} — "
                    f"*{item['vol']} м³* "
                    f"(№{item['inv']})\n"
                )
                saved += 1

        if saved == 0:
            st.error("Нет заполненных рейсов")
            st.stop()

        msg += "--------------------------\n✅ *Всем удачного рейса!*"
        st.session_state.wa_msg = msg

        # ---------- АВТО-СОХРАНЕНИЕ ----------
        df = pd.DataFrame(st.session_state.db)
        file_created = None

        try:
            df.to_excel("otgruzka.xlsx", index=False)
            file_created = "otgruzka.xlsx"
        except Exception:
            df.to_csv("otgruzka.csv", index=False)
            file_created = "otgruzka.csv"

        st.session_state.last_file = file_created
        st.success(f"✅ Сохранено рейсов: {saved}")

    # ==================================================
    # WHATSAPP + СКАЧИВАНИЕ
    # ==================================================
    if "wa_msg" in st.session_state:
        st.divider()
        st.subheader("📲 Отправка в WhatsApp")
        st.code(st.session_state.wa_msg)

        encoded = urllib.parse.quote(st.session_state.wa_msg)
        wa_url = f"https://api.whatsapp.com/send?text={encoded}"

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

        if st.session_state.last_file and os.path.exists(st.session_state.last_file):
            with open(st.session_state.last_file, "rb") as f:
                st.download_button(
                    f"📥 Скачать {st.session_state.last_file}",
                    data=f,
                    file_name=st.session_state.last_file
                )

# ======================================================
# 🧱 ОПЕРАТОР
# ======================================================
with tab2:
    st.subheader("Последние отгрузки")
    if st.session_state.db:
        st.dataframe(
            pd.DataFrame(st.session_state.db).tail(20),
            use_container_width=True
        )
    else:
        st.info("Данных пока нет")

# ======================================================
# 🚛 ВОДИТЕЛИ
# ======================================================
with tab3:
    st.subheader("Лента рейсов")
    if st.session_state.db:
        for r in reversed(st.session_state.db[-20:]):
            st.success(
                f"{r['Дата']} {r['Время']} | "
                f"{r['Водитель']} | "
                f"{r['Объем']} м³ | "
                f"{r['Объект']}"
            )
    else:
        st.info("Пока пусто")
