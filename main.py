import flet as ft
import sqlite3
import os
import pandas as pd
from datetime import datetime

# ======================================================
# БАЗА ДАННЫХ
# ======================================================
def init_db():
    data_dir = os.getenv("FLET_APP_STORAGE_DATA", os.getcwd())
    db_path = os.path.join(data_dir, "database.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS shipments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dt TEXT, tm TEXT, plant TEXT, object TEXT, grade TEXT, 
        volume REAL)""")
    conn.commit()
    return conn

db_conn = init_db()

# ======================================================
# ИНТЕРФЕЙС
# ======================================================
def main(page: ft.Page):
    page.title = "Бетон Завод PRO"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10

    # Поля ввода для первой вкладки
    plant_dd = ft.Dropdown(label="Завод", options=[ft.dropdown.Option("УЧАСТОК"), ft.dropdown.Option("888")], expand=True)
    obj_in = ft.TextField(label="📍 Объект", expand=True)
    grade_in = ft.TextField(label="💎 Марка", value="300", expand=True)
    vol_in = ft.TextField(label="Объем (м³)", value="0", keyboard_type=ft.KeyboardType.NUMBER, expand=True)

    # Таблица для второй вкладки (Журнал)
    log_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Дата")),
            ft.DataColumn(ft.Text("Объект")),
            ft.DataColumn(ft.Text("м³")),
        ],
        rows=[]
    )

    def load_logs():
        """Загрузка данных из базы в таблицу"""
        cursor = db_conn.execute("SELECT dt, object, volume FROM shipments ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        log_table.rows.clear()
        for r in rows:
            log_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(str(r[0]))), ft.DataCell(ft.Text(str(r[1]))), ft.DataCell(ft.Text(str(r[2])))]))
        page.update()

    def save_order(e):
        try:
            now = datetime.now()
            db_conn.execute("INSERT INTO shipments (dt, tm, plant, object, grade, volume) VALUES (?, ?, ?, ?, ?, ?)",
                            (now.strftime("%d.%m.%y"), now.strftime("%H:%M"), plant_dd.value, obj_in.value, grade_in.value, float(vol_in.value)))
            db_conn.commit()
            obj_in.value = ""
            vol_in.value = "0"
            page.snack_bar = ft.SnackBar(ft.Text("Сохранено!"))
            page.snack_bar.open = True
            load_logs()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка: {ex}"))
            page.snack_bar.open = True
            page.update()

    def export_excel(e):
        """Экспорт в Excel на Android"""
        try:
            df = pd.read_sql_query("SELECT * FROM shipments", db_conn)
            # Сохраняем во временную папку приложения
            temp_path = os.path.join(os.getenv("FLET_APP_STORAGE_DATA", os.getcwd()), "journal.xlsx")
            df.to_excel(temp_path, index=False, engine='openpyxl')
            
            page.snack_bar = ft.SnackBar(ft.Text(f"Файл создан: {temp_path}"))
            page.snack_bar.open = True
            page.update()
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Ошибка Excel: {ex}"))
            page.snack_bar.open = True
            page.update()

    # Вкладки
    tabs = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="ОТГРУЗКА", content=ft.Column([
                ft.Text("📝 Новый заказ", size=20, weight="bold"),
                plant_dd, obj_in, grade_in, vol_in,
                ft.ElevatedButton("ЗАПИСАТЬ", on_click=save_order, bgcolor=ft.colors.GREEN, color=ft.colors.WHITE, width=400)
            ], tight=True, spacing=15)),
            ft.Tab(text="ЖУРНАЛ", content=ft.Column([
                ft.Row([
                    ft.Text("📋 Последние 10", size=20, weight="bold"),
                    ft.IconButton(ft.icons.FILE_DOWNLOAD, on_click=export_excel, icon_color="blue")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Column([log_table], scroll=ft.ScrollMode.ALWAYS, height=400)
            ], spacing=15))
        ],
        expand=1
    )

    page.add(
        ft.AppBar(title=ft.Text("БЕТОН ЗАВОД PRO"), bgcolor=ft.colors.ORANGE_700, color=ft.colors.WHITE),
        tabs
    )
    load_logs()

ft.app(target=main)
    ft.app(target=main)
