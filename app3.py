import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse

st.set_page_config(page_title="Бетон Завод (Групповая рассылка)", layout="wide")

# Список имен для выбора (без телефонов, так как шлем в общую группу)
DRIVERS_NAMES = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов", "Дмитрий Кузнецов", 
    "Андрей Попов", "Михаил Новиков", "Артем Морозов", "Игорь Волков", 
    "Виктор Васильев", "Николай Федоров"
]

if 'db' not in st.session_state:
    st.session_state.db = []

st.title("🏗 Управление отгрузкой (Группа WhatsApp)")

tab1, tab2, tab3 = st.tabs(["📝 Бухгалтерия (Массово)", "🧱 Оператор", "🚛 Водители"])

# --- 1. ВКЛАДКА БУХГАЛТЕРИИ ---
with tab1:
    st.subheader("Формирование рейса")
    
    col_a, col_b = st.columns(2)
    with col_a:
        obj = st.text_input("📍 Объект", placeholder="Напр: ЖК Астана")
    with col_b:
        grade = st.selectbox("💎 Марка", ["М100", "М150", "М200", "М250", "М300", "М350", "М400"])
    
    st.write("---")
    st.write("**Выберите водителей этого рейса:**")
    
    batch_entries = []
    cols = st.columns(2)
    for i, name in enumerate(DRIVERS_NAMES):
        with cols[i % 2]:
            is_active = st.checkbox(name, key=f"active_{name}")
            if is_active:
                v = st.number_input(f"Кубы ({name})", min_value=0.0, step=0.5, key=f"v_{name}")
                n = st.text_input(f"Накл. № ({name})", key=f"n_{name}")
                batch_entries.append({"name": name, "vol": v, "inv": n})
            st.write("---")

    if st.button("💾 СОХРАНИТЬ И СФОРМИРОВАТЬ СООБЩЕНИЕ"):
        if obj and batch_entries:
            # Формируем заголовок сообщения
            report_msg = f"🏗 *ОТГРУЗКА БЕТОНА* 🏗\n📍 *Объект:* {obj}\n💎 *Марка:* {grade}\n--------------------------\n"
            
            for item in batch_entries:
                if item['vol'] > 0:
                    entry = {
                        "Время": datetime.now().strftime("%H:%M"),
                        "Объект": obj, "Марка": grade, 
                        "Объем": item['vol'], "Водитель": item['name'], 
                        "Накладная": item['inv']
                    }
                    st.session_state.db.append(entry)
                    # Добавляем строку в общее сообщение
                    report_msg += f"🚛 {item['name']}: *{item['vol']} м³* (№{item['inv']})\n"
            
            report_msg += "--------------------------\n✅ *Всем удачного рейса!*"
            st.session_state['group_msg'] = report_msg
            st.success("Данные сохранены!")
        else:
            st.error("Заполните объект и выберите водителей!")

    # Кнопка отправки в ОБЩУЮ ГРУППУ
    if 'group_msg' in st.session_state:
        st.subheader("📲 Отправка в группу")
        st.code(st.session_state['group_msg']) # Предпросмотр текста
        
        encoded_report = urllib.parse.quote(st.session_state['group_msg'])
        # Ссылка просто открывает WhatsApp, бухгалтер сам выбирает группу из списка чатов
        wa_group_url = f"https://wa.me/?text={encoded_report}"
        
        st.markdown(f"""
            <a href="{wa_group_url}" target="_blank">
                <button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-weight:bold; cursor:pointer;">
                    🟢 ОТПРАВИТЬ ВЕСЬ СПИСОК В WHATSAPP ГРУППУ
                </button>
            </a>
        """, unsafe_allow_html=True)

# --- 2. ВКЛАДКА ОПЕРАТОРА (СУММАРНО) ---
with tab2:
    if st.session_state.db:
        df = pd.DataFrame(st.session_state.db)
        st.subheader("Суммарно к загрузке:")
        summary = df.groupby(['Объект', 'Марка'])['Объем'].sum().reset_index()
        st.table(summary)
        st.write("Детальный список машин:")
        st.dataframe(df)
        if st.button("🗑 Очистить историю"):
            st.session_state.db = []
            st.rerun()

# --- 3. ВКЛАДКА ВОДИТЕЛЕЙ ---
with tab3:
    if not st.session_state.db:
        st.info("Нет активных заявок")
    else:
        for item in reversed(st.session_state.db):
            st.info(f"📍 {item['Объект']} | {item['Водитель']} | {item['Объем']} м³ | Накл: {item['Накладная']}")
