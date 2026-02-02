import flet as ft
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

    # Input field for FIN
    fin_input = ft.TextField(label="Enter FIN", width=300)
    result_text = ft.Text(value="", selectable=True)

    def register_household(e):
        fin_raw = fin_input.value.strip()
        fin, household_id, already_registered, error = registry.register_household(fin_raw)

        if error:
            result_text.value = f"Error: {error}"
        elif already_registered:
            result_text.value = f"Household with FIN {fin} is already registered. ID: {household_id}"
        else:
            result_text.value = f"Successfully registered FIN {fin}. Household ID: {household_id}"

        page.update()

    # Registration button
    register_button = ft.ElevatedButton("Register Household", on_click=register_household)

    # Layout
    page.add(
        ft.Column(
            controls=[
                ft.Text("Household Registration Portal", size=20, weight="bold"),
                fin_input,
                register_button,
                result_text
            ],
            alignment="start",
            spacing=20
        )
    )

# Run the Flet app
ft.app(target=main)
