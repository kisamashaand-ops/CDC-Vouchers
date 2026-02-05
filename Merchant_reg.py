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

def ensure_csv_exists_with_header():
    if not os.path.exists(CSV_FILENAME):
        with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()

def find_existing_merchant(bank_name: str, account_number: str,
                           merchant_name: str, account_holder: str) -> tuple[str | None, bool]:
    """
    Returns (Merchant_ID, exact_match_flag).
    - Merchant_ID if any merchant has same bank+account.
    - exact_match_flag True if all fields match (name, bank, account, holder).
    """
    if not os.path.exists(CSV_FILENAME):
        return None, False

    with open(CSV_FILENAME, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_bank = (row.get("Bank_Name") or "").strip()
            existing_acct = (row.get("Account_Number") or "").strip()
            if existing_bank == bank_name and existing_acct == account_number:
                existing_id = (row.get("Merchant_ID") or "").strip() or None
                # Check full match
                same_name = (row.get("Merchant_Name") or "").strip().lower() == merchant_name.lower()
                same_holder = (row.get("Account_Holder_Name") or "").strip().lower() == account_holder.lower()
                if same_name and same_holder:
                    return existing_id, True
                else:
                    return existing_id, False
    return None, False

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
    page.bgcolor = ft.Colors.BLUE_50   # soft background

    # Input fields
    merchant_name = ft.TextField(label="Merchant Name", width=400, bgcolor=ft.Colors.WHITE, border_radius=8)
    bank_name = ft.Dropdown(
        label="Bank Name",
        options=[ft.dropdown.Option(b) for b in sorted(ALLOWED_BANKS)],
        width=400
    )
    account_number = ft.TextField(
        label="Account Number (9 digits)",
        width=400,
        max_length=9,
        bgcolor=ft.Colors.WHITE,
        border_radius=8
    )
    account_holder = ft.TextField(label="Account Holder Name", width=400, bgcolor=ft.Colors.WHITE, border_radius=8)

    result_text = ft.Text(value="", selectable=True, size=16)

    def register_clicked(e):
        m_name = merchant_name.value.strip()
        b_name = bank_name.value.strip() if bank_name.value else ""
        acct_num = account_number.value.strip()
        acct_holder = account_holder.value.strip()

        # Validation
        if b_name not in ALLOWED_BANKS:
            result_text.value = "❌ Invalid Bank Name."
            result_text.color = ft.Colors.RED
        elif not (acct_num.isdigit() and len(acct_num) == 9):
            result_text.value = "❌ Account Number must be exactly 9 digits."
            result_text.color = ft.Colors.RED
        elif not all([m_name, b_name, acct_num, acct_holder]):
            result_text.value = "❌ All fields are required."
            result_text.color = ft.Colors.RED
        else:
            existing_id, exact_match = find_existing_merchant(b_name, acct_num, m_name, acct_holder)
            if existing_id:
                if exact_match:
                    result_text.value = f"⚠️ Already registered. Merchant_ID: {existing_id}"
                    result_text.color = ft.Colors.ORANGE
                else:
                    result_text.value = "⚠️ Please double check the information you entered."
                    result_text.color = ft.Colors.ORANGE
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
                result_text.color = ft.Colors.GREEN

        page.update()

    register_button = ft.ElevatedButton(
        "Submit",
        on_click=register_clicked,
        bgcolor=ft.Colors.BLUE,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
    )

    # Card-style container
    card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("🏦 Merchant Registration Portal", size=26, weight="bold", color=ft.Colors.BLUE_900),
                merchant_name,
                bank_name,
                account_number,
                account_holder,
                register_button,
                result_text
            ],
            alignment="center",
            spacing=20
        ),
        bgcolor=ft.Colors.WHITE,
        border_radius=12,
        padding=30,
        shadow=ft.BoxShadow(blur_radius=12, color=ft.Colors.BLUE_GREY_200)
    )

    # Center everything
    page.add(
        ft.Row(
            controls=[card],
            alignment="center"
        )
    )

ft.app(target=main)
