from flask import Flask, request, Response, redirect, url_for
import csv
import os

app = Flask(__name__)

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
    """
    Returns existing Merchant_ID if either Merchant_Name OR Account_Number
    is already registered. Otherwise returns None.
    """
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
    """
    Reads existing merchant.csv and returns the next Merchant_ID in sequence:
    M001, M002, ...
    """
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

@app.get("/")
def home():
    html = """
    <!doctype html>
    <html>
      <head><meta charset="utf-8"><title>Merchant Registration</title></head>
      <body style="font-family: Arial; max-width: 720px; margin: 40px;">
        <h2>Merchant Registration</h2>

        <form method="POST" action="/register">
          <label>Merchant Name</label><br/>
          <input name="Merchant_Name" required style="width:100%; padding:8px;"/><br/><br/>

          <label>Bank Name</label><br/>
            <select name="Bank_Name" required style="width:100%; padding:8px;">
                <option value="" disabled selected>Select a bank</option>
                <option>DBS Bank Ltd</option>
                <option>OCBC Bank</option>
                <option>UOB Bank</option>
                <option>Maybank Singapore</option>
                <option>Standard Chartered Bank</option>
                <option>HSBC Singapore</option>
                <option>POSB Bank</option>
                <option>Citibank Singapore</option>
                <option>RHB Bank Berhad</option>
                <option>Bank of China Singapore</option>
            </select><br/><br/>

            <label>Account Number (9 digits)</label><br/>
            <input name="Account_Number"
                required
                inputmode="numeric"
                pattern="\\d{9}"
                maxlength="9"
                title="Account Number must be exactly 9 digits"
                style="width:100%; padding:8px;"/><br/><br/>

          <label>Account Holder Name</label><br/>
          <input name="Account_Holder_Name" required style="width:100%; padding:8px;"/><br/><br/>

          <button type="submit" style="padding:10px 14px;">Submit</button>
        </form>
      </body>
    </html>
    """
    return Response(html, mimetype="text/html")

@app.post("/register")
def register():
    merchant_name = (request.form.get("Merchant_Name") or "").strip()
    bank_name = (request.form.get("Bank_Name") or "").strip()
    account_number = (request.form.get("Account_Number") or "").strip()
    account_holder = (request.form.get("Account_Holder_Name") or "").strip()

    if bank_name not in ALLOWED_BANKS:
        return Response(
            f"""
            <p style="font-family:Arial; margin:40px;">
            Invalid Bank Name.
            <br/><br/>
            <a href="/">Go back</a>
            </p>
            """,
            mimetype="text/html",
            status=400
        )

    if not (account_number.isdigit() and len(account_number) == 9):
        return Response(
            f"""
            <p style="font-family:Arial; margin:40px;">
            Invalid Account Number.
            <br/><br/>
            <a href="/">Go back</a>
            </p>
            """,
            mimetype="text/html",
            status=400
        )

    if not all([merchant_name, bank_name, account_number, account_holder]):
        return redirect(url_for("home"))

    existing_id = find_existing_merchant_id(merchant_name, account_number)
    if existing_id:
        html = f"""
        <!doctype html>
        <html>
        <head><meta charset="utf-8"><title>Registered</title></head>
        <body style="font-family: Arial; max-width: 720px; margin: 40px;">
            <p><b>Already Registered</b></p>
            <p><b>Merchant_ID:</b> {existing_id}</p>
            <p><a href="/">Submit again</a></p>
        </body>
        </html>
        """
        return Response(html, mimetype="text/html")

    merchant_id = get_next_merchant_id()

    row = {
        "Merchant_ID": merchant_id,
        "Merchant_Name": merchant_name,
        "Bank_Name": bank_name,
        "Account_Number": account_number,
        "Account_Holder_Name": account_holder
    }

    append_to_csv(row)

    html = f"""
    <!doctype html>
    <html>
      <head><meta charset="utf-8"><title>Registered</title></head>
      <body style="font-family: Arial; max-width: 720px; margin: 40px;">
        <p><b>Merchant_ID:</b> {merchant_id}</p>
        <p><a href="/">Submit again</a></p>
      </body>
    </html>
    """
    return Response(html, mimetype="text/html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)