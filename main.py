import flet as ft
import sqlite3
from datetime import datetime

# ======================================================
# БАЗА ДАННЫХ
# ======================================================
def init_db():
    conn = sqlite3.connect("database.db", check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS shipments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dt TEXT, tm TEXT, plant TEXT, object TEXT, grade TEXT, 
        driver TEXT, volume REAL, price_m3 REAL, 
        total REAL, paid REAL, debt REAL, invoice TEXT)""")
    conn.commit()
    return conn

db_conn = init_db()

# ======================================================
# ИНТЕРФЕЙС
# ======================================================
def main(page: ft.Page):
    page.title = "Бетон Завод PRO"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 400 # Эмуляция мобильного экрана
    
    # Поля ввода
    plant_dropdown = ft.Dropdown(
        label="Завод погрузки",
        options=[ft.dropdown.Option("УЧАСТОК"), ft.dropdown.Option("888")],
        width=400
    )
    obj_input = ft.TextField(label="📍 Объект", width=400)
    grade_input = ft.TextField(label="💎 Марка бетона", value="300", width=400)
    volume_input = ft.TextField(label="Объем (м³)", value="0", width=400, keyboard_type=ft.KeyboardType.NUMBER)
    
    def save_order(e):
        if not obj_input.value or float(volume_input.value) <= 0:
            page.snack_bar = ft.SnackBar(ft.Text("Заполните объект и объем!"))
            page.snack_bar.open = True
            page.update()
            return
        
        # Сохранение в базу
        now = datetime.now()
        db_conn.execute("""INSERT INTO shipments (dt, tm, plant, object, grade, volume) 
                           VALUES (?, ?, ?, ?, ?, ?)""", 
                        (now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), 
                         plant_dropdown.value, obj_input.value, grade_input.value, float(volume_input.value)))
        db_conn.commit()
        
        page.dialog = ft.AlertDialog(title=ft.Text("Успех!"), content=ft.Text("Заказ сохранен в базу."))
        page.dialog.open = True
        page.update()

    # Сборка экрана
    page.add(
        ft.AppBar(title=ft.Text("БЕТОН ЗАВОД PRO"), bgcolor=ft.colors.ORANGE_700, color=ft.colors.WHITE),
        ft.Column([
            ft.Text("📝 Оформление отгрузки", size=20, weight="bold"),
            plant_dropdown,
            obj_input,
            grade_input,
            volume_input,
            ft.ElevatedButton("СОХРАНИТЬ В БАЗУ", on_click=save_order, 
                              style=ft.ButtonStyle(bgcolor=ft.colors.GREEN, color=ft.colors.WHITE), width=400),
        ], scroll=ft.ScrollMode.AUTO)
    )

if __name__ == "__main__":
    ft.app(target=main)
