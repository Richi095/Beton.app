import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Бетон Завод PRO", layout="centered")

# Список водителей
DRIVERS_LIST = [
    "Алексей Петров", "Иван Иванов", "Сергей Соколов", "Дмитрий Кузнецов", 
    "Андрей Попов", "Михаил Новиков", "Артем Морозов", "Игорь Волков", 
    "Виктор Васильев", "Николай Федоров"
]

# Стили
st.markdown("""
    <style>
    .order-card { background-color: white; padding: 15px; border-radius: 10px; border-left: 8px solid #28a745; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); color: black; }
    .stCheckbox { margin-bottom: -15px; }
    </style>
    """, unsafe_allow_html=True)

if 'db' not in st.session_state:
    st.session_state.db = []

st.title("🏗 Управление Заводом")

tab1, tab2, tab3 = st.tabs(["📝 Бухгалтерия", "🧱 Оператор", "🚛 Водители"])

# --- 1. ВКЛАДКА БУХГАЛТЕРИИ ---
with tab1:
    st.subheader("Массовая заявка (на весь рейс)")
    
    # Общие данные для всех машин
    col_a, col_b = st.columns(2)
    with col_a:
        obj = st.text_input("📍 Объект (куда)")
    with col_b:
        grade = st.selectbox("💎 Марка бетона", ["М100", "М150", "М200", "М250", "М300", "М350", "М400"])
    
    st.write("---")
    st.write("**Выберите водителей и укажите объем:**")
    
    selected_drivers_data = []
    # Сетка для выбора водителей (в 2 колонки для удобства на телефоне)
    cols = st.columns(2)
    for i, name in enumerate(DRIVERS_LIST):
        with cols[i % 2]:
            is_selected = st.checkbox(name, key=f"check_{name}")
            if is_selected:
                v = st.number_input(f"Кубы для {name.split()[0]}", min_value=0.0, step=0.5, key=f"vol_{name}")
                n = st.text_input(f"Накладная для {name.split()[0]}", key=f"inv_{name}")
                selected_drivers_data.append({"name": name, "vol": v, "inv": n})

    if st.button("🚀 ОТПРАВИТЬ ВСЕ ЗАЯВКИ СРАЗУ"):
        if obj and selected_drivers_data:
            for item in selected_drivers_data:
                if item['vol'] > 0 and item['inv']:
                    new_entry = {
                        "Время": datetime.now().strftime("%H:%M"),
                        "Объект": obj, "Марка": grade, 
                        "Объем": item['vol'], "Водитель": item['name'], 
                        "Накладная": item['inv']
                    }
                    st.session_state.db.append(new_entry)
            st.success(f"Готово! Добавлено заявок: {len(selected_drivers_data)}")
            st.rerun()
        else:
            st.error("Укажите объект и выберите хотя бы одного водителя с объемом и накладной!")

# --- 2. ВКЛАДКА ОПЕРАТОРА ---
with tab2:
    if st.session_state.db:
        df = pd.DataFrame(st.session_state.db)
        st.subheader("Сводка для загрузки")
        summary = df.groupby("Марка")["Объем"].sum().reset_index()
        st.table(summary)
        st.write("Список всех машин:")
        st.dataframe(df[["Время", "Объект", "Водитель", "Объем", "Марка", "Накладная"]])
        if st.button("🗑 Очистить всё (в конце смены)"):
            st.session_state.db = []
            st.rerun()
    else:
        st.info("Заявок нет")

# --- 3. ВКЛАДКА ВОДИТЕЛЕЙ ---
with tab3:
    st.subheader("Список рейсов")
    filter_driver = st.selectbox("Показать рейсы для:", ["Все водители"] + DRIVERS_LIST)
    
    if not st.session_state.db:
        st.info("На сегодня заявок нет")
    else:
        for item in reversed(st.session_state.db):
            if filter_driver == "Все водители" or filter_driver == item["Водитель"]:
                st.markdown(f"""
                <div class="order-card">
                    <b>📍 {item['Объект']}</b> | {item['Время']}<br>
                    🏗 <b>{item['Марка']} — {item['Объем']} м³</b><br>
                    👤 {item['Водитель']} | 📄 №{item['Накладная']}
                </div>
                """, unsafe_allow_html=True)

# Боковая панель Excel
if st.session_state.db:
    df_export = pd.DataFrame(st.session_state.db)
    csv = df_export.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button("📥 СКАЧАТЬ ОТЧЕТ EXCEL", csv, "otchet_beton.csv")


