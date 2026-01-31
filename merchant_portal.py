from flask import Flask, request, render_template_string, Response, session, redirect, url_for
import csv
import os
import json
import time
from datetime import datetime
from io import StringIO
from data_structure import HouseholdRegistry

app = Flask(__name__)
app.secret_key = "secret_key_for_session" 

# --- 配置文件路径 ---
TRANSACTIONS_CSV = "data/transactions.csv"
ACTIVATIONS_JSON = "data/activations.json"
MERCHANT_CSV = "merchant.csv"
DATA_DIR = "data"

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 初始化 Registry
registry = HouseholdRegistry(
    data_dir="data",
    households_csv="households.csv",
    voucher_state_json="voucher_state.json"
)

# --- Helper Functions ---

def get_merchant_details(merchant_id):
    """
    从 merchant.csv 读取单个商户银行信息
    """
    if not os.path.exists(MERCHANT_CSV):
        return None
    
    with open(MERCHANT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Merchant_ID") == merchant_id:
                return row
    return None

def get_all_merchants_map():
    """
    读取所有商户信息并返回一个字典: { 'M001': {Details}, 'M002': {Details}... }
    用于生成总表时快速查找
    """
    merchants = {}
    if os.path.exists(MERCHANT_CSV):
        with open(MERCHANT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                merchants[row.get("Merchant_ID")] = row
    return merchants

def ensure_transaction_csv_exists():
    headers = [
        "Transaction_ID", "Household_ID", "Merchant_ID", 
        "Transaction_Date_Time", "Voucher_Code", 
        "Denomination_Used", "Amount_Redeemed", 
        "Payment_Status", "Remarks"
    ]
    if not os.path.exists(TRANSACTIONS_CSV):
        with open(TRANSACTIONS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

def get_next_transaction_id():
    ensure_transaction_csv_exists()
    max_id = 0
    with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid_str = row.get("Transaction_ID", "")
            if tid_str.startswith("TX") and tid_str[2:].isdigit():
                current_id = int(tid_str[2:])
                if current_id > max_id:
                    max_id = current_id
    return f"TX{max_id + 1:05d}"

# --- Routes ---

@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        mid = request.form.get("merchant_id", "").strip()
        details = get_merchant_details(mid)
        
        # 允许登录逻辑 (如果商户表不存在，允许测试)
        if details or not os.path.exists(MERCHANT_CSV):
            session["merchant_id"] = mid
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid Merchant ID. Please register first."

    # 在登录页面下方添加了 "Admin Download" 区域
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Merchant Login</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light d-flex align-items-center justify-content-center" style="height: 100vh;">
        <div class="card shadow-sm p-4" style="max-width: 400px; width: 100%;">
            <div class="text-center mb-4">
                <h3 class="fw-bold">CDC Merchant Portal</h3>
                <p class="text-muted">Log in to redeem vouchers</p>
            </div>
            
            {f'<div class="alert alert-danger">{error}</div>' if error else ''}

            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Merchant ID</label>
                    <input type="text" name="merchant_id" class="form-control" placeholder="e.g. M001" required>
                </div>
                <div class="d-grid">
                    <button type="submit" class="btn btn-primary">Login</button>
                </div>
            </form>

            <hr class="my-4">
            
            <div class="text-center">
                <p class="small text-muted mb-2">Administration</p>
                <form action="/admin/download_master_csv" method="POST">
                    <button type="submit" class="btn btn-outline-dark btn-sm w-100">
                        📥 Download Master Report (All Data)
                    </button>
                </form>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/logout")
def logout():
    session.pop("merchant_id", None)
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "merchant_id" not in session:
        return redirect(url_for("login"))
    
    mid = session["merchant_id"]
    merchant_info = get_merchant_details(mid)
    
    bank_info_html = ""
    if merchant_info:
        bank_info_html = f"""
        <div class="alert alert-info mt-3">
            <strong>Receiving Account:</strong> {merchant_info.get('Bank_Name')} - {merchant_info.get('Account_Number')}<br>
            <small class="text-muted">Holder: {merchant_info.get('Account_Holder_Name')}</small>
        </div>
        """

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Merchant Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-dark mb-4">
            <div class="container">
                <span class="navbar-brand mb-0 h1">Merchant Portal: {mid}</span>
                <a href="/logout" class="btn btn-outline-light btn-sm">Logout</a>
            </div>
        </nav>

        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-8">
                    
                    {bank_info_html}

                    <div class="card shadow-sm mb-4">
                        <div class="card-header bg-success text-white">
                            <h4 class="mb-0">Redeem Voucher</h4>
                        </div>
                        <div class="card-body p-4">
                            <form action="/redeem" method="POST">
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Scan/Enter Customer Barcode</label>
                                    <input type="text" name="barcode" class="form-control form-control-lg" placeholder="13-digit barcode..." required autofocus>
                                </div>
                                <div class="d-grid">
                                    <button type="submit" class="btn btn-success btn-lg">Verify & Redeem</button>
                                </div>
                            </form>
                        </div>
                    </div>

                    <div class="card shadow-sm">
                        <div class="card-header bg-primary text-white">
                            <h4 class="mb-0">Transaction Reports</h4>
                        </div>
                        <div class="card-body p-4 text-center">
                            <p class="text-muted">Download logs for bank reconciliation.</p>
                            <a href="/history" class="btn btn-primary w-100">View History & Download CSV</a>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/redeem", methods=["POST"])
def redeem():
    if "merchant_id" not in session:
        return redirect(url_for("login"))

    merchant_id = session["merchant_id"]
    barcode_input = request.form.get("barcode", "").strip()
    
    if not os.path.exists(ACTIVATIONS_JSON):
        return render_result("Error", "System error: No activation records found.", "danger")

    found_record = None
    with open(ACTIVATIONS_JSON, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for record in data:
                if record.get("barcode") == barcode_input:
                    found_record = record
                    break
        except json.JSONDecodeError:
            pass

    if not found_record:
        return render_result("Invalid Barcode", f"Barcode '{barcode_input}' not found.", "danger")

    voucher_codes = found_record.get("voucher_codes", [])
    if not voucher_codes:
        return render_result("Empty Voucher", "No vouchers linked to this barcode.", "warning")

    registry.load_voucher_state()
    
    valid_vouchers_details = [] 
    household_id_ref = ""
    already_used = False
    total_amount = 0

    try:
        for code in voucher_codes:
            hid, denom, idx = registry.parse_voucher_code(code)
            household_id_ref = hid
            array_idx = idx - 1
            
            current_state_list = registry.household_voucher_state.get(hid, {}).get(str(denom), [])
            
            if array_idx < 0 or array_idx >= len(current_state_list):
                return render_result("Error", f"Voucher index out of range for {code}", "danger")
            
            if current_state_list[array_idx] == 1:
                already_used = True
                break
            
            valid_vouchers_details.append({
                "code": code,
                "denom": denom,
                "hid": hid,
                "idx": array_idx
            })
            total_amount += denom

    except Exception as e:
        return render_result("Error", f"Data format error: {str(e)}", "danger")

    if already_used:
        return render_result("Declined", "This voucher set has ALREADY been redeemed.", "danger")

    # Update State
    for item in valid_vouchers_details:
        registry.household_voucher_state[item["hid"]][str(item["denom"])][item["idx"]] = 1
    
    registry.save_voucher_state() 

    # Write Transaction
    ensure_transaction_csv_exists()
    tx_id = get_next_transaction_id()
    tx_time = datetime.now().strftime("%Y%m%d%H%M%S")
    
    with open(TRANSACTIONS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        count = len(valid_vouchers_details)
        for i, item in enumerate(valid_vouchers_details):
            remarks = "Final denomination used" if i == count - 1 else str(i + 1)
            writer.writerow([
                tx_id,
                item["hid"],
                merchant_id,
                tx_time,
                item["code"],
                f"${item['denom']}.00",
                f"${total_amount}.00",
                "Completed",
                remarks
            ])

    return render_result(
        "Redemption Successful!", 
        f"Transaction <b>{tx_id}</b> processed.<br>Amount: <b>${total_amount}</b>", 
        "success"
    )

def render_result(title, message, color):
    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Result</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container py-5">
            <div class="card shadow-sm border-{color}">
                <div class="card-header bg-{color} text-white">
                    <h4>{title}</h4>
                </div>
                <div class="card-body">
                    <p class="lead">{message}</p>
                    <a href="/dashboard" class="btn btn-secondary">Back to Dashboard</a>
                    <a href="/history" class="btn btn-primary ms-2">View History</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/history", methods=["GET", "POST"])
def history():
    if "merchant_id" not in session:
        return redirect(url_for("login"))
        
    merchant_id = session["merchant_id"]
    merchant_info = get_merchant_details(merchant_id)
    transactions = []
    
    if os.path.exists(TRANSACTIONS_CSV):
        with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Merchant_ID") == merchant_id:
                    transactions.append(row)
    
    rows_html = ""
    for row in transactions:
        rows_html += f"""
        <tr>
            <td>{row['Transaction_ID']}</td>
            <td>{row['Transaction_Date_Time']}</td>
            <td>{row['Voucher_Code']}</td>
            <td>{row['Denomination_Used']}</td>
            <td>{row['Payment_Status']}</td>
            <td>{row['Remarks']}</td>
        </tr>
        """

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>History</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <nav class="navbar navbar-dark bg-dark mb-4">
            <div class="container">
                <span class="navbar-brand mb-0 h1">History: {merchant_id}</span>
                <a href="/dashboard" class="btn btn-outline-light btn-sm">Back</a>
            </div>
        </nav>
        <div class="container">
            <div class="alert alert-secondary">
                <strong>Bank Account linked:</strong> 
                {merchant_info.get('Bank_Name', 'N/A') if merchant_info else 'Unknown'} 
                ({merchant_info.get('Account_Number', 'N/A') if merchant_info else ''})
            </div>
            
            <div class="d-flex justify-content-end mb-3">
                <form action="/download_csv" method="POST">
                    <button type="submit" class="btn btn-success">Download CSV for Reconciliation</button>
                </form>
            </div>

            <div class="card shadow-sm">
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-striped table-hover mb-0" style="font-size:0.9rem;">
                            <thead class="table-dark">
                                <tr>
                                    <th>Tx ID</th>
                                    <th>Date/Time</th>
                                    <th>Voucher Code</th>
                                    <th>Denom</th>
                                    <th>Status</th>
                                    <th>Remarks</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html if rows_html else '<tr><td colspan="6" class="text-center">No transactions found.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/download_csv", methods=["POST"])
def download_csv():
    """下载特定商户的历史记录"""
    if "merchant_id" not in session:
        return redirect(url_for("login"))
        
    merchant_id = session["merchant_id"]
    
    # 获取银行信息
    merchant_info = get_merchant_details(merchant_id)
    
    output = StringIO()
    
    fieldnames = [
        "Transaction_ID", "Household_ID", "Merchant_ID", 
        "Transaction_Date_Time", "Voucher_Code", 
        "Denomination_Used", "Amount_Redeemed", 
        "Payment_Status", "Remarks"
    ]
    
    # 可选：如果需要在商户自己的表里也加上银行信息，可以在这里加
    # 但根据你的要求，主要是总表需要详细的银行信息。
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    if os.path.exists(TRANSACTIONS_CSV):
        with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Merchant_ID") == merchant_id:
                    clean_row = {k: row.get(k, "") for k in fieldnames}
                    writer.writerow(clean_row)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=transactions_{merchant_id}.csv"}
    )

# --- 新增：管理员功能 ---
@app.route("/admin/download_master_csv", methods=["POST"])
def download_master_csv():
    """
    生成包含所有商户、所有家庭、以及银行信息的总表。
    """
    
    # 1. 获取所有商户的银行信息映射
    merchants_map = get_all_merchants_map()
    
    output = StringIO()
    
    # 2. 定义包含银行信息的总表头
    master_fieldnames = [
        "Transaction_ID", "Household_ID", "Merchant_ID", 
        "Merchant_Name", "Bank_Name", "Account_Number", "Account_Holder_Name", # 新增列
        "Transaction_Date_Time", "Voucher_Code", 
        "Denomination_Used", "Amount_Redeemed", 
        "Payment_Status", "Remarks"
    ]
    
    writer = csv.DictWriter(output, fieldnames=master_fieldnames)
    writer.writeheader()
    
    if os.path.exists(TRANSACTIONS_CSV):
        with open(TRANSACTIONS_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 3. 查找该笔交易对应的商户信息
                mid = row.get("Merchant_ID")
                m_info = merchants_map.get(mid, {})
                
                # 4. 构建合并后的行
                combined_row = {
                    "Transaction_ID": row.get("Transaction_ID"),
                    "Household_ID": row.get("Household_ID"),
                    "Merchant_ID": mid,
                    "Merchant_Name": m_info.get("Merchant_Name", "Unknown"),
                    "Bank_Name": m_info.get("Bank_Name", "Unknown"),
                    "Account_Number": m_info.get("Account_Number", "Unknown"),
                    "Account_Holder_Name": m_info.get("Account_Holder_Name", "Unknown"),
                    "Transaction_Date_Time": row.get("Transaction_Date_Time"),
                    "Voucher_Code": row.get("Voucher_Code"),
                    "Denomination_Used": row.get("Denomination_Used"),
                    "Amount_Redeemed": row.get("Amount_Redeemed"),
                    "Payment_Status": row.get("Payment_Status"),
                    "Remarks": row.get("Remarks")
                }
                
                writer.writerow(combined_row)
    
    # 5. 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=Master_Redemption_Report_{timestamp}.csv"}
    )

if __name__ == "__main__":
    app.run(port=5002, debug=True)