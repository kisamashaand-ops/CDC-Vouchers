import flet as ft
from flet import Colors
from data_structure import HouseholdRegistry

# One registry instance (in-memory + persistence)
registry = HouseholdRegistry(
    data_dir="data",
    households_csv="households.csv",
    voucher_state_json="voucher_state.json",
    voucher_counts={2: 80, 5: 32, 10: 45}
)

def main(page: ft.Page):
    page.title = "Household Registration"
    page.scroll = "adaptive"
    page.bgcolor = Colors.BLUE_50   # soft background color

    # Single input field
    id_input = ft.TextField(
        label="Enter ID",
        width=300,
        bgcolor=Colors.WHITE,
        border_radius=10,
    )
    result_text = ft.Text(value="", selectable=True, color=Colors.BLACK)

    # Clear inputs/outputs when page is loaded/refreshed
    def on_page_load(e):
        id_input.value = ""
        result_text.value = ""
        page.update()

    page.on_connect = on_page_load   # triggers when page is refreshed/loaded

    def register_household(e):
        id_raw = id_input.value.strip()

        if not id_raw:
            result_text.value = "❌ Error: Please enter your ID."
            result_text.Color = colors.RED
            page.update()
            return

        fin, household_id, already_registered, error = registry.register_household(id_raw)

        if error:
            result_text.value = f"❌ Error: {error}"
            result_text.color = Colors.RED
        elif already_registered:
            result_text.value = f"ℹ️ Household with ID {fin} is already registered. Household ID: {household_id}"
            result_text.color = Colors.ORANGE
        else:
            result_text.value = f"✅ Your ID was successfully registered. Household ID: {household_id}"
            result_text.color = Colors.GREEN

        page.update()

    # Registration button
    register_button = ft.ElevatedButton(
        "Register Household",
        on_click=register_household,
        bgcolor=Colors.BLUE,
        color=Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )

    # Card-style container
    card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("🏠 Household Registration Portal", size=24, weight="bold", color=Colors.BLUE_900),
                id_input,
                register_button,
                result_text
            ],
            alignment="center",
            spacing=20
        ),
        bgcolor=Colors.WHITE,
        border_radius=15,
        padding=30,
        shadow=ft.BoxShadow(blur_radius=15, color=Colors.BLUE_GREY_200)
    )

    # Center everything on the page
    page.add(
        ft.Row(
            controls=[card],
            alignment="center"
        )
    )

# Run the Flet app
ft.app(target=main)
