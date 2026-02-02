import flet as ft
import csv
import os

CSV_FILENAME = "merchant.csv"
CSV_HEADERS = [
    "Merchant_ID",
    "Merchant_Name",
    "Bank_Name",
    "Account_Number",
    "Account_Holder_Name"
]

ALLOWED_BANKS = {
    "DBS Bank Ltd",
    "OCBC Bank",
    "UOB Bank",
    "Maybank Singapore",
    "Standard Chartered Bank",
    "HSBC Singapore",
    "POSB Bank",
    "Citibank Singapore",
    "RHB Bank Berhad",
    "Bank of China Singapore",
}

def normalize_branch_code(branch_code: str) -> str:
    bc = (branch_code or "").strip()
    return bc.zfill(3) if bc.isdigit() else bc

def ensure_csv_exists_with_header():
    if not os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()

def find_existing_merchant_id(merchant_name: str, account_number: str) -> str | None:
    if not os.path.exists(CSV_FILENAME):
        return None
    name_key = merchant_name.strip().lower()
    acct_key = account_number.strip()
    with open(CSV_FILENAME, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_name = (row.get("Merchant_Name") or "").strip().lower()
            existing_acct = (row.get("Account_Number") or "").strip()
            if existing_name == name_key or existing_acct == acct_key:
                return (row.get("Merchant_ID") or "").strip() or None
    return None

def get_next_merchant_id() -> str:
    ensure_csv_exists_with_header()
    max_num = 0
    with open(CSV_FILENAME, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = (row.get("Merchant_ID") or "").strip()
            if mid.startswith("M") and mid[1:].isdigit():
                max_num = max(max_num, int(mid[1:]))
    return f"M{max_num + 1:03d}"

def append_to_csv(row: dict):
    ensure_csv_exists_with_header()
    with open(CSV_FILENAME, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row)

def main(page: ft.Page):
    page.title = "Merchant Registration"
    page.scroll = "adaptive"

    # Input fields
    merchant_name = ft.TextField(label="Merchant Name", width=400)
    bank_name = ft.Dropdown(
        label="Bank Name",
        options=[ft.dropdown.Option(b) for b in sorted(ALLOWED_BANKS)],
        width=400
    )
    account_number = ft.TextField(
        label="Account Number (9 digits)",
        width=400,
        max_length=9
    )
    account_holder = ft.TextField(label="Account Holder Name", width=400)

    result_text = ft.Text(value="", selectable=True, color="blue")

    def register_clicked(e):
        m_name = merchant_name.value.strip()
        b_name = bank_name.value.strip() if bank_name.value else ""
        acct_num = account_number.value.strip()
        acct_holder = account_holder.value.strip()

        # Validation
        if b_name not in ALLOWED_BANKS:
            result_text.value = "❌ Invalid Bank Name."
        elif not (acct_num.isdigit() and len(acct_num) == 9):
            result_text.value = "❌ Account Number must be exactly 9 digits."
        elif not all([m_name, b_name, acct_num, acct_holder]):
            result_text.value = "❌ All fields are required."
        else:
            existing_id = find_existing_merchant_id(m_name, acct_num)
            if existing_id:
                result_text.value = f"⚠️ Already Registered. Merchant_ID: {existing_id}"
            else:
                merchant_id = get_next_merchant_id()
                row = {
                    "Merchant_ID": merchant_id,
                    "Merchant_Name": m_name,
                    "Bank_Name": b_name,
                    "Account_Number": acct_num,
                    "Account_Holder_Name": acct_holder
                }
                append_to_csv(row)
                result_text.value = f"✅ Registered successfully. Merchant_ID: {merchant_id}"

        page.update()

    register_button = ft.ElevatedButton("Submit", on_click=register_clicked)

    page.add(
        ft.Column(
            controls=[
                ft.Text("Merchant Registration", size=22, weight="bold"),
                merchant_name,
                bank_name,
                account_number,
                account_holder,
                register_button,
                result_text
            ],
            spacing=15
        )
    )

ft.app(target=main)
