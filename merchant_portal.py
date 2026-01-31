import flet as ft
import csv
import os
import json
from datetime import datetime
from data_structure import HouseholdRegistry

# ================== CONFIG ==================

DATA_DIR = "data"
TRANSACTIONS_CSV = f"{DATA_DIR}/transactions.csv"
ACTIVATIONS_JSON = f"{DATA_DIR}/activations.json"
MERCHANT_CSV = "merchant.csv"

os.makedirs(DATA_DIR, exist_ok=True)

registry = HouseholdRegistry(
    data_dir="data",
    households_csv="households.csv",
    voucher_state_json="voucher_state.json"
)

# ================== HELPERS ==================

def ensure_transaction_csv_exists():
    if not os.path.exists(TRANSACTIONS_CSV):
        with open(TRANSACTIONS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                "Transaction_ID", "Household_ID", "Merchant_ID",
                "Transaction_Date_Time", "Voucher_Code",
                "Denomination_Used", "Amount_Redeemed",
                "Payment_Status", "Remarks"
            ])

def get_next_transaction_id():
    ensure_transaction_csv_exists()
    max_id = 0
    with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tid = r.get("Transaction_ID", "")
            if tid.startswith("TX") and tid[2:].isdigit():
                max_id = max(max_id, int(tid[2:]))
    return f"TX{max_id + 1:05d}"

def get_merchant_details(mid):
    if not os.path.exists(MERCHANT_CSV):
        return None
    with open(MERCHANT_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("Merchant_ID") == mid:
                return r
    return None

# ================== APP ==================

def main(page: ft.Page):
    page.title = "CDC Merchant Portal"
    page.window_width = 420
    page.window_height = 720
    page.theme_mode = ft.ThemeMode.LIGHT

    merchant_id = None  # <-- SAFE STATE STORAGE

    def clear():
        page.controls.clear()

    # ================= LOGIN =================

    merchant_input = ft.TextField(label="Merchant ID", autofocus=True)
    error_text = ft.Text(color=ft.Colors.RED)

    def show_login():
        clear()
        merchant_input.value = ""
        error_text.value = ""

        page.controls.append(
            ft.Column(
                [
                    ft.Text("CDC Merchant Portal", size=24, weight=ft.FontWeight.BOLD),
                    merchant_input,
                    error_text,
                    ft.ElevatedButton("Login", on_click=handle_login),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )
        page.update()

    def handle_login(e):
        nonlocal merchant_id
        mid = merchant_input.value.strip()

        if get_merchant_details(mid) or not os.path.exists(MERCHANT_CSV):
            merchant_id = mid
            show_dashboard()
        else:
            error_text.value = "Invalid Merchant ID"
            page.update()

    # ================= DASHBOARD =================

    barcode_input = ft.TextField(label="Scan / Enter Barcode")

    def show_dashboard():
        clear()
        barcode_input.value = ""

        page.controls.append(
            ft.Column(
                [
                    ft.Text("Merchant Dashboard", size=20, weight=ft.FontWeight.BOLD),
                    barcode_input,
                    ft.ElevatedButton("Redeem Voucher", on_click=redeem_voucher),
                    ft.OutlinedButton("View History", on_click=show_history),
                    ft.TextButton("Logout", on_click=logout),
                ],
                expand=True,
            )
        )
        page.update()

    # ================= REDEEM =================

    def redeem_voucher(e):
        if not merchant_id:
            show_login()
            return

        barcode = barcode_input.value.strip()

        if not os.path.exists(ACTIVATIONS_JSON):
            show_result("Error", "Activation file missing", ft.Colors.RED)
            return

        with open(ACTIVATIONS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)

        record = next((r for r in data if r.get("barcode") == barcode), None)
        if not record:
            show_result("Invalid", "Barcode not found", ft.Colors.RED)
            return

        registry.load_voucher_state()

        vouchers = []
        total = 0

        for code in record["voucher_codes"]:
            hid, denom, idx = registry.parse_voucher_code(code)
            idx -= 1

            if registry.household_voucher_state[hid][str(denom)][idx] == 1:
                show_result("Declined", "Voucher already redeemed", ft.Colors.RED)
                return

            vouchers.append((hid, denom, idx, code))
            total += denom

        for hid, denom, idx, _ in vouchers:
            registry.household_voucher_state[hid][str(denom)][idx] = 1

        registry.save_voucher_state()

        tx_id = get_next_transaction_id()
        ts = datetime.now().strftime("%Y%m%d%H%M%S")

        with open(TRANSACTIONS_CSV, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for i, (hid, denom, _, code) in enumerate(vouchers):
                w.writerow([
                    tx_id,
                    hid,
                    merchant_id,
                    ts,
                    code,
                    f"${denom}.00",
                    f"${total}.00",
                    "Completed",
                    "Final" if i == len(vouchers) - 1 else str(i + 1)
                ])

        show_result("Success", f"{tx_id} | Amount ${total}", ft.Colors.GREEN)

    # ================= HISTORY =================

    def show_history():
        clear()
        rows = []

        if os.path.exists(TRANSACTIONS_CSV):
            with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["Merchant_ID"] == merchant_id:
                        rows.append(
                            ft.DataRow(
                                cells=[
                                    ft.DataCell(ft.Text(r["Transaction_ID"])),
                                    ft.DataCell(ft.Text(r["Transaction_Date_Time"])),
                                    ft.DataCell(ft.Text(r["Voucher_Code"])),
                                    ft.DataCell(ft.Text(r["Denomination_Used"])),
                                ]
                            )
                        )

        page.controls.append(
            ft.Column(
                [
                    ft.Text("Transaction History", size=20, weight=ft.FontWeight.BOLD),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Tx ID")),
                            ft.DataColumn(ft.Text("Date")),
                            ft.DataColumn(ft.Text("Voucher")),
                            ft.DataColumn(ft.Text("Amount")),
                        ],
                        rows=rows,
                    ),
                    ft.OutlinedButton("Back", on_click=show_dashboard),
                ],
                expand=True,
            )
        )
        page.update()

    # ================= RESULT =================

    def show_result(title, message, color):
        clear()
        page.controls.append(
            ft.Column(
                [
                    ft.Text(title, size=22, weight=ft.FontWeight.BOLD, color=color),
                    ft.Text(message),
                    ft.ElevatedButton("Back", on_click=show_dashboard),
                ],
                expand=True,
            )
        )
        page.update()

    # ================= LOGOUT =================

    def logout(e):
        nonlocal merchant_id
        merchant_id = None
        show_login()

    # ================= START =================

    show_login()

# ================== RUN ==================

ft.app(target=main)



# ---------------- RUN ----------------

#if __name__ == "__main__": 
 #   ft.app(target=main, view=ft.AppView.WEB_BROWSER)
    #port = int(os.environ.get("PORT", 8080)) 
    #ft.app(target=main, view=ft.AppView.WEB, port=port)
