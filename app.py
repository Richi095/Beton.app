import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Бетон Завод", layout="centered")

# Память приложения
if 'db' not in st.session_state:
    st.session_state.db = []

st.title("🏗 БЕТОН ЗАВОД")

tab1, tab2 = st.tabs(["📝 Бухгалтерия", "🚛 Водители"])

with tab1:
    st.subheader("Новая заявка")
    obj = st.text_input("📍 Объект (Куда)")
    grade = st.selectbox("💎 Марка бетона", ["М100", "М150", "М200", "М250", "М300", "М350", "М400"])
    vol = st.number_input("📏 Кубатура (м³)", min_value=0.0, step=0.5)
    driver = st.selectbox("👤 Водитель", [f"Водитель {i}" for i in range(1, 11)])
    inv = st.text_input("📄 Номер накладной #")
    
    if st.button("✅ СОХРАНИТЬ ЗАЯВКУ"):
        if obj and inv:
            new_data = {"Дата": datetime.now().strftime("%H:%M"), "Объект": obj, "Марка": grade, "Объем": vol, "Водитель": driver, "Накладная": inv}
            st.session_state.db.append(new_data)
            st.success("Заявка успешно добавлена!")
        else:
            st.error("Заполните объект и номер накладной!")

with tab2:
    st.subheader("План отгрузки на сегодня")
    if not st.session_state.db:
        st.info("Заявок пока нет.")
    else:
        for item in reversed(st.session_state.db):
            st.info(f"📍 {item['Объект']} | Марка: {item['Марка']} | Объем: {item['Объем']}м³ | №{item['Накладная']} | Водитель: {item['Водитель']}")

if st.session_state.db:
    st.divider()
    df = pd.DataFrame(st.session_state.db)
    st.download_button("📥 Скачать Excel (CSV)", df.to_csv(index=False).encode('utf-8-sig'), "otchet_zavod.csv")


