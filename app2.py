import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse # Для кодирования текста ссылки

st.set_page_config(page_title="Бетон Завод PRO", layout="centered")

# СПИСОК ВОДИТЕЛЕЙ И ИХ ТЕЛЕФОНОВ
# Указывай номер в формате 77071234567 (без + и пробелов)
DRIVERS_DATA = {
    "Алексей Петров": "77071112233",
    "Иван Иванов": "77074445566",
    "Сергей Соколов": "77077778899",
    # Добавь сюда остальных...
}

if 'db' not in st.session_state:
    st.session_state.db = []

st.title("🏗 Бетон Завод + WhatsApp")

tab1, tab2, tab3 = st.tabs(["📝 Бухгалтерия", "🧱 Оператор", "🚛 Водители"])

with tab1:
    st.subheader("Новая заявка")
    obj = st.text_input("📍 Объект")
    grade = st.selectbox("💎 Марка", ["М100", "М150", "М200", "М250", "М300", "М350", "М400"])
    
    selected_name = st.selectbox("👤 Выберите водителя", list(DRIVERS_DATA.keys()))
    vol = st.number_input("📏 Кубатура (м³)", min_value=0.0, step=0.5)
    inv = st.text_input("📄 Накладная №")
    
    if st.button("✅ СОХРАНИТЬ И ПОДГОТОВИТЬ WHATSAPP"):
        if obj and inv and vol > 0:
            # 1. Сохраняем в базу приложения
            new_entry = {
                "Время": datetime.now().strftime("%H:%M"),
                "Объект": obj, "Марка": grade, "Объем": vol, 
                "Водитель": selected_name, "Накладная": inv
            }
            st.session_state.db.append(new_entry)
            
            # 2. Формируем сообщение для WhatsApp
            phone = DRIVERS_DATA[selected_name]
            message = f"📢 НОВАЯ ЗАЯВКА!\n📍 Объект: {obj}\n🏗 Бетон: {grade}\n📏 Объем: {vol} м³\n📄 Накладная: №{inv}\n🕒 Время: {new_entry['Время']}"
            
            # Кодируем текст для ссылки
            encoded_msg = urllib.parse.quote(message)
            wa_link = f"https://wa.me/{phone}?text={encoded_msg}"
            
            st.success("Заявка сохранена!")
            # Кнопка для перехода в WhatsApp
            st.markdown(f"""
                <a href="{wa_link}" target="_blank">
                    <button style="background-color: #25D366; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; width: 100%;">
                        🟢 ОТПРАВИТЬ ВОДИТЕЛЮ В WHATSAPP
                    </button>
                </a>
            """, unsafe_allow_html=True)
        else:
            st.error("Заполните все данные!")

# Остальные вкладки (Оператор и Водители) остаются как были
with tab2:
    if st.session_state.db:
        st.table(pd.DataFrame(st.session_state.db))
with tab3:
    for item in reversed(st.session_state.db):
        st.info(f"{item['Объект']} | {item['Водитель']} | {item['Объем']}м³")

