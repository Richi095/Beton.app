import streamlit as st
import pandas as pd
from datetime import datetime
import urllib.parse
import os

# Имя файла для хранения данных
DB_FILE = "otgruzka.xlsx"

st.set_page_config(page_title="Управление отгрузкой бетона", layout="wide")

# ======================================================
# ЗАГРУЗКА ДАННЫХ (SESSION STATE)
# ======================================================
if "db" not in st.session_state:
    if os.path.exists(DB_FILE):
        try:
            # Пытаемся загрузить существующий Excel
            st.session_state.db = pd.read_excel(DB_FILE).to_dict('records')
        except Exception:
            st.session_state.db = []
    else:
        st.session_state.db = []

if "wa_msg" not in st.session_state:
    st.session_state.wa_msg = None

# Список водителей
ALL_DRIVERS = ["Алексей Петров", "Иван Иванов", "Сергей Соколов", "Дмитрий Кузнецов", "Андрей Попов", "Михаил Новиков", "Артем Морозов", "Игорь Волков", "Виктор Васильев", "Николай Федоров"]

# ======================================================
# ИНТЕРФЕЙС
# ======================================================
st.title("🏗 Управление отгрузкой бетона")

tab1, tab2, tab3 = st.tabs(["📝 Бухгалтерия", "🧱 Оператор", "🚛 Водители"])

with tab1:
    st.subheader("Формирование нового рейса")
    
    col_a, col_b = st.columns(2)
    with col_a:
        obj = st.text_input("📍 Объект", placeholder="Например: Ц1444")
    with col_b:
        grade = st.selectbox("💎 Марка бетона", ["М100","М150","М200","М250","М300","М350","М400"])

    selected_drivers = st.multiselect("👥 Выберите водителей", ALL_DRIVERS)

    if selected_drivers:
        st.markdown("### 🚛 Данные по машинам")
        batch = []
        total_volume = 0.0
        
        for i, name in enumerate(selected_drivers):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.write(f"**{name}**")
            with c2:
                vol = st.number_input("Кубы", min_value=0.0, step=0.5, key=f"v_{i}")
            with c3:
                inv = st.text_input("Накладная №", key=f"n_{i}")
            
            if vol > 0:
                batch.append({"name": name, "vol": vol, "inv": inv})
                total_volume += vol

        st.metric("🚚 Общий объем рейса", f"{total_volume} м³")

        if st.button("💾 СОХРАНИТЬ И СФОРМИРОВАТЬ СПИСОК"):
            if not obj:
                st.error("Укажите объект!")
            else:
                new_records = []
                msg = f"🏗 *ОТГРУЗКА БЕТОНА* 🏗\n📍 *Объект:* {obj}\n💎 *Марка:* {grade}\n" + "-"*20 + "\n"
                
                for entry in batch:
                    record = {
                        "Дата": datetime.now().strftime("%d.%m.%Y"),
                        "Время": datetime.now().strftime("%H:%M"),
                        "Объект": obj,
                        "Марка": grade,
                        "Водитель": entry["name"],
                        "Объем": entry["vol"],
                        "Накладная": entry["inv"]
                    }
                    st.session_state.db.append(record)
                    new_records.append(record)
                    msg += f"🚛 {entry['name']} — *{entry['vol']} м³* (№{entry['inv']})\n"
                
                # Сохранение в файл
                df = pd.DataFrame(st.session_state.db)
                df.to_excel(DB_FILE, index=False)
                
                st.session_state.wa_msg = msg + "-"*20 + "\n✅ *Всем удачного рейса!*"
                st.success(f"Записи сохранены в {DB_FILE}")
                st.rerun()

    # Блок WhatsApp
    if st.session_state.wa_msg:
        st.divider()
        st.code(st.session_state.wa_msg)
        encoded_msg = urllib.parse.quote(st.session_state.wa_msg)
        st.markdown(f"""
            <a href="https://wa.me/?text={encoded_msg}" target="_blank">
                <button style="width:100%; background:#25D366; color:white; border:none; padding:12px; border-radius:8px; font-weight:bold; cursor:pointer;">
                    🟢 ОТПРАВИТЬ В WHATSAPP
                </button>
            </a>
        """, unsafe_allow_html=True)

with tab2:
    st.subheader("Журнал отгрузок")
    if st.session_state.db:
        df_display = pd.DataFrame(st.session_state.db)
        st.dataframe(df_display.iloc[::-1], use_container_width=True) # Последние сверху
    else:
        st.info("Данных пока нет")

with tab3:
    st.subheader("Последние рейсы")
    if st.session_state.db:
        for r in reversed(st.session_state.db[-10:]):
            st.info(f"🚛 **{r['Водитель']}** | {r['Объем']} м³ | {r['Объект']} (№{r['Накладная']})")
