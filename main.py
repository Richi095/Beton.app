import flet as ft
def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.add(ft.Text("ПРОВЕРКА: СИСТЕМА РАБОТАЕТ!", size=30, color="blue"))
ft.app(target=main)
