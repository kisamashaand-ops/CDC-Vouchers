from flask import Flask, request, render_template
from data_structure import HouseholdRegistry

app = Flask(__name__)

# One registry instance (in-memory + persistence)
registry = HouseholdRegistry(
    data_dir="data",
    households_csv="households.csv",
    voucher_state_json="voucher_state.json",
    voucher_counts={2: 80, 5: 32, 10: 45}
)

@app.route("/")
def home():
    return render_template("household_register.html")

@app.route("/household_registration", methods=["POST"])
def household_registration():
    fin_raw = request.form.get("fin", "")
    fin, household_id, already_registered, error = registry.register_household(fin_raw)

    return render_template(
        "household_regi_result.html",
        fin=fin,
        household_id=household_id,
        already_registered=already_registered,
        error=error
    )

if __name__ == "__main__":
    app.run(debug=True)
