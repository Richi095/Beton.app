import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Бетон Завод", layout="centered")

# Данные хранятся в памяти (для теста)
if 'db' not in st.session_state:
    st.session_state.db = []

st.title("🏗 БЕТОН ЗАВОД")

tab1, tab2 = st.tabs(["📝 Бухгалтерия", "🚛 Водители"])

with tab1:
    st.subheader("Новая заявка")
    obj = st.text_input("📍 Объект")
    grade = st.selectbox("💎 Марка", ["М100", "М150", "М200", "М250", "М300", "М350", "М400"])
    vol = st.number_input("📏 Кубатура (м³)", min_value=0.0)
    driver = st.selectbox("👤 Водитель", ["Иван", "Алексей", "Водитель 3", "Водитель 4"])
    inv = st.text_input("📄 Накладная #")
    
    if st.button("✅ СОХРАНИТЬ"):
        new_data = {"Дата": datetime.now().strftime("%H:%M"), "Объект": obj, "Марка": grade, "Объем": vol, "Водитель": driver, "Накладная": inv}
        st.session_state.db.append(new_data)
        st.success("Добавлено!")

with tab2:
    st.subheader("План отгрузки")
    for item in reversed(st.session_state.db):
        st.info(f"📍 {item['Объект']} | {item['Марка']} | {item['Объем']} м³ | Накл: {item['Накладная']} | 👤 {item['Водитель']}")

if st.session_state.db:
    df = pd.DataFrame(st.session_state.db)
    st.download_button("📥 Скачать Excel", df.to_csv(index=False).encode('utf-8-sig'), "beton.csv")
