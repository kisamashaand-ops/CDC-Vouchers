import flet as ft
import json
import os
import time
import random
import barcode
import base64
from barcode.writer import ImageWriter
from data_structure import HouseholdRegistry

# Initialize registry
registry = HouseholdRegistry(
    data_dir="data",
    households_csv="households.csv",
    voucher_state_json="voucher_state.json",
    voucher_counts={2: 80, 5: 32, 10: 45}
)

ACTIVATION_LOG = "data/activations.json"
BARCODE_DIR = "data/barcodes"

os.makedirs(BARCODE_DIR, exist_ok=True)

def encode_image_base64(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def generate_barcode():
    """Generate a 13-digit numeric barcode string"""
    return "".join([str(random.randint(0, 9)) for _ in range(13)])

def save_barcode_image(barcode_number):
    ean = barcode.get("ean13", barcode_number, writer=ImageWriter())
    filename = os.path.join(BARCODE_DIR, str(barcode_number))
    result = ean.save(filename)
    if isinstance(result, tuple):
        result = result[0]
    return result, ean.get_fullcode()

def save_activation(barcode_number, voucher_codes):
    os.makedirs("data", exist_ok=True)

    try:
        with open(ACTIVATION_LOG, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append({
        "barcode": barcode_number,
        "voucher_codes": voucher_codes,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

    with open(ACTIVATION_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Activation saved:", barcode_number, voucher_codes)


def main(page: ft.Page):
    page.title = "CDC Voucher Activation"
    page.window_width = 600
    page.window_height = 700

    household_id_input = ft.TextField(label="Enter Household ID")
    message = ft.Text(value="", color="red")

    selected_vouchers = []

    # ✅ store UI reference locally (don’t use session for Controls)
    proceed_btn_ref = {"btn": None}

    def go_home(e=None):
        page.controls.clear()
        page.add(household_id_input, ft.ElevatedButton("Login", on_click=login), message)
        page.update()

    def login(e):
        hid = (household_id_input.value or "").strip()
        if not hid or hid not in registry.household_voucher_state:
            message.value = "Invalid Household ID."
            page.update()
            return

        message.value = ""
        show_voucher_grid(hid)

    def show_voucher_grid(hid):
        page.controls.clear()
        selected_vouchers.clear()

        state = registry.household_voucher_state[hid]
        buttons = []

        total_balance = sum(int(denom) for denom, arr in state.items() for val in arr if val == 0)

        page.add(
            ft.Text(f"Household {hid} - Select vouchers", size=20, weight="bold"),
            ft.Text(f"Total Available Balance: ${total_balance}", size=18, color="blue", weight="bold")
        )

        for denom, arr in state.items():
            for idx, val in enumerate(arr):
                code = registry.format_voucher_code(hid, int(denom), idx + 1)

                btn = ft.ElevatedButton(
                    content=ft.Text(f"${denom} #{idx+1}"),
                    width=120,
                    bgcolor="white" if val == 0 else "grey",
                    disabled=(val == 1),
                )

                def on_click(ev, c=code, b=btn):
                    if c in selected_vouchers:
                        selected_vouchers.remove(c)
                        b.bgcolor = "white"
                    else:
                        selected_vouchers.append(c)
                        b.bgcolor = "lightblue"
                    toggle_proceed_button()
                    page.update()

                btn.on_click = on_click
                buttons.append(btn)

        rows = []
        for i in range(0, len(buttons), 2):
            row = ft.Row([buttons[i]] + ([buttons[i + 1]] if i + 1 < len(buttons) else []))
            rows.append(row)

        proceed_btn = ft.ElevatedButton(
            content=ft.Text("Proceed to Activation"),
            visible=False,
            on_click=lambda ev: activate_vouchers(hid)
        )

        voucher_column = ft.Column(rows, scroll="auto", expand=True)
        page.add(voucher_column, proceed_btn)
        page.update()

        # ✅ save reference
        proceed_btn_ref["btn"] = proceed_btn

    def toggle_proceed_button():
        btn = proceed_btn_ref["btn"]
        if btn is None:
            return
        btn.visible = len(selected_vouchers) > 0

    def activate_vouchers(hid):
        barcode_number = generate_barcode()
        barcode_file, full_code = save_barcode_image(barcode_number)

        save_activation(full_code, selected_vouchers)

        page.controls.clear()
        page.add(
            ft.Text("Activation Successful!", size=22, weight="bold", color="green"),
            ft.Text(f"Barcode Number:\n{full_code}", selectable=True),
            ft.Image(src=f"data:image/png;base64,{encode_image_base64(barcode_file)}",width=300,height=150,),
            ft.Text("Activated Vouchers:", size=18, weight="bold"),
            ft.Text("\n".join(selected_vouchers), selectable=True),
            ft.ElevatedButton("Back to Home", on_click=go_home)
        )
        page.update()

    go_home()

if __name__ == "__main__": 
    #ft.app(target=main, view=ft.AppView.WEB_BROWSER)
    port = int(os.environ.get("PORT", 8080)) 
    ft.app(target=main, view=ft.AppView.WEB, port=port)

