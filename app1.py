import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Бетон Завод (Умный выбор)", layout="wide")

# ПОЛНЫЙ СПИСОК ВОДИТЕЛЕЙ (добавляй/удаляй имена здесь)
ALL_DRIVERS = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов", "Дмитрий Кузнецов", 
    "Андрей Попов", "Михаил Новиков", "Артем Морозов", "Игорь Волков", 
    "Виктор Васильев", "Николай Федоров"
]

if 'db' not in st.session_state:
    st.session_state.db = []

st.title("🏗 Управление отгрузкой")

tab1, tab2, tab3 = st.tabs(["📝 Бухгалтерия", "🧱 Оператор", "🚛 Водители"])

# --- 1. ВКЛАДКА БУХГАЛТЕРИИ ---
with tab1:
    st.subheader("Формирование нового рейса")
    
    col_a, col_b = st.columns(2)
    with col_a:
        obj = st.text_input("📍 Объект", placeholder="Куда везем?")
    with col_b:
        grade = st.selectbox("💎 Марка", ["М100", "М150", "М200", "М250", "М300", "М350", "М400"])
    
    # НОВИНКА: Выбираем только нужных водителей
    selected_drivers = st.multiselect("👥 Выберите водителей для этого рейса:", ALL_DRIVERS)
    
    st.write("---")
    
    batch_entries = []
    if selected_drivers:
        st.write("**Данные по выбранным машинам:**")
        # Создаем поля ввода только для тех, кого выбрали
        for name in selected_drivers:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"🚛 **{name}**")
            with col2:
                v = st.number_input(f"Кубы", min_value=0.0, step=0.5, key=f"v_{name}")
            with col3:
                n = st.text_input(f"Накл. №", key=f"n_{name}")
            batch_entries.append({"name": name, "vol": v, "inv": n})
            st.write("") # Отступ
    else:
        st.info("Выберите хотя бы одного водителя выше, чтобы начать ввод")

    if st.button("💾 СОХРАНИТЬ И СФОРМИРОВАТЬ СПИСОК") and selected_drivers:
        if obj:
            # Текст сообщения для WhatsApp
            report_msg = f"🏗 *ОТГРУЗКА БЕТОНА* 🏗\n📍 *Объект:* {obj}\n💎 *Марка:* {grade}\n--------------------------\n"
            
            valid_entries = 0
            for item in batch_entries:
                if item['vol'] > 0:
                    entry = {
                        "Время": datetime.now().strftime("%H:%M"),
                        "Объект": obj, "Марка": grade, 
                        "Объем": item['vol'], "Водитель": item['name'], 
                        "Накладная": item['inv']
                    }
                    st.session_state.db.append(entry)
                    report_msg += f"🚛 {item['name']}: *{item['vol']} м³* (№{item['inv']})\n"
                    valid_entries += 1
            
            if valid_entries > 0:
                report_msg += "--------------------------\n✅ *Всем удачного рейса!*"
                st.session_state['group_msg'] = report_msg
                st.success(f"Сохранено заявок: {valid_entries}")
            else:
                st.warning("Вы не указали объем ни для одного водителя")
        else:
            st.error("Введите название объекта!")

    # Кнопка для WhatsApp
    if 'group_msg' in st.session_state:
        st.divider()
        st.subheader("📲 Отправка в группу")
        st.code(st.session_state['group_msg'])
        
        encoded_report = urllib.parse.quote(st.session_state['group_msg'])
        wa_group_url = f"https://wa.me/?text={encoded_report}"
        
        st.markdown(f"""
            <a href="{wa_group_url}" target="_blank">
                <button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; cursor:pointer; font-size:16px;">
                    🟢 ОТПРАВИТЬ СПИСОК В ГРУППУ WHATSAPP
                </button>
            </a>
        """, unsafe_allow_html=True)

# Вкладки Оператор и Водители остаются для контроля
with tab2:
    if st.session_state.db:
        st.table(pd.DataFrame(st.session_state.db).tail(10))
with tab3:
    for item in reversed(st.session_state.db):
        st.info(f"{item['Объект']} | {item['Водитель']} | {item['Объем']}м³")


