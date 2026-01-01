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

EXCEL_FILE = "otgruzka.xlsx"

ALL_DRIVERS = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов",
    "Дмитрий Кузнецов", "Андрей Попов", "Михаил Новиков",
    "Артем Морозов", "Игорь Волков",
    "Виктор Васильев", "Николай Федоров"
]

# ======================================================
# ЗАГРУЗКА / ИНИЦИАЛИЗАЦИЯ ДАННЫХ
# ======================================================
if "db" not in st.session_state:
    if os.path.exists(EXCEL_FILE):
        st.session_state.db = pd.read_excel(EXCEL_FILE).to_dict("records")
    else:
        st.session_state.db = []

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
    else
