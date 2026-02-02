import csv
import json
import os
import re

class HouseholdRegistry:
    """
    Household Registry with validation and persistence.
    - Validates FIN/NRIC format
    - Stores households in CSV/JSON
    """

    # Singapore NRIC/FIN format: prefix S/T/F/G, 7 digits, checksum letter
    FIN_NRIC_PATTERN = re.compile(r"^[STFG]\d{7}[A-Z]$")

    def __init__(self,
                 data_dir="data",
                 households_csv="households.csv",
                 voucher_state_json="voucher_state.json",
                 voucher_counts=None):
        self.data_dir = data_dir
        self.households_csv_path = os.path.join(data_dir, households_csv)
        self.voucher_state_json_path = os.path.join(data_dir, voucher_state_json)
        self.voucher_counts = voucher_counts or {2: 80, 5: 32, 10: 45}

        # In-memory
        self.fin_to_household = {}
        self.household_voucher_state = {}

        # Boot
        self.ensure_data_dir()
        self.load_households()
        self.load_voucher_state()
        self.ensure_voucher_state_for_all()
        self.save_voucher_state()

    # ---------- Utilities ----------
    def ensure_data_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)

    def normalize_fin(self, fin: str) -> str:
        return fin.strip().upper()

    def is_valid_fin_or_nric(self, fin: str) -> bool:
        """Check if input matches FIN/NRIC pattern."""
        return bool(self.FIN_NRIC_PATTERN.match(fin))

    # ---------- Persistence ----------
    def load_households(self):
        if not os.path.exists(self.households_csv_path):
            return
        with open(self.households_csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fin = row.get("FIN", "").strip()
                hid = row.get("Household_ID", "").strip()
                if fin and hid:
                    self.fin_to_household[fin] = hid

    def load_voucher_state(self):
        if not os.path.exists(self.voucher_state_json_path):
            return
        with open(self.voucher_state_json_path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                self.household_voucher_state.update(data)

    def save_households(self):
        with open(self.households_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["FIN", "Household_ID"])
            for fin, hid in self.fin_to_household.items():
                writer.writerow([fin, hid])

    def save_voucher_state(self):
        with open(self.voucher_state_json_path, "w", encoding="utf-8") as f:
            json.dump(self.household_voucher_state, f, indent=2)

    # ---------- Core logic ----------
    def get_next_household_id(self) -> str:
        if not self.fin_to_household:
            return "H0001"
        max_num = max(int(hid[1:]) for hid in self.fin_to_household.values() if hid.startswith("H"))
        return f"H{max_num + 1:04d}"

    def init_voucher_state(self, household_id: str):
        self.household_voucher_state[household_id] = {
            str(denom): [0] * count for denom, count in self.voucher_counts.items()
        }

    def ensure_voucher_state_for_all(self):
        for hid in self.fin_to_household.values():
            if hid not in self.household_voucher_state:
                self.init_voucher_state(hid)

    # ---------- Main API ----------
    def register_household(self, fin_raw: str):
        fin = self.normalize_fin(fin_raw)
        if not fin:
            return "", "", False, "FIN/NRIC is required."
        if not self.is_valid_fin_or_nric(fin):
            return fin, "", False, "Invalid FIN/NRIC format."

        # Existing
        if fin in self.fin_to_household:
            hid = self.fin_to_household[fin]
            already = True
            if hid not in self.household_voucher_state:
                self.init_voucher_state(hid)
                self.save_voucher_state()
            return fin, hid, already, None

        # New
        hid = self.get_next_household_id()
        self.fin_to_household[fin] = hid
        self.init_voucher_state(hid)

        # Persist
        self.save_households()
        self.save_voucher_state()

        return fin, hid, False, None
