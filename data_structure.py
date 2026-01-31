import csv
import json
import os

class HouseholdRegistry:
    """
    Encapsulates:
    - FIN -> Household_ID mapping (registration)
    - Voucher state initialization (3B)
    - Persistence to households.csv + voucher_state.json
    - In-memory structures for fast lookup
    """

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
        self.fin_to_household = {}          # FIN -> Household_ID
        self.household_voucher_state = {}   # Household_ID -> {"2":[0/1...], "5":[...], "10":[...]}

        # Boot
        self.ensure_data_dir()
        self.load_households()
        self.load_voucher_state()
        self.ensure_voucher_state_for_all()
        self.save_voucher_state()  # keep json consistent

    # ---------- Utilities ----------
    def ensure_data_dir(self):
        os.makedirs(self.data_dir, exist_ok=True)

    def normalize_fin(self, fin: str) -> str:
        return fin.strip().upper()

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
        self.ensure_data_dir()
        with open(self.households_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["FIN", "Household_ID"])
            for fin, hid in self.fin_to_household.items():
                writer.writerow([fin, hid])

    def save_voucher_state(self):
        self.ensure_data_dir()
        with open(self.voucher_state_json_path, "w", encoding="utf-8") as f:
            json.dump(self.household_voucher_state, f, indent=2)

    # ---------- Core logic ----------
    def get_next_household_id(self) -> str:
        """
        Incremental: H0001, H0002, ...
        """
        if not self.fin_to_household:
            return "H0001"

        max_num = 0
        for hid in self.fin_to_household.values():
            if hid.startswith("H") and hid[1:].isdigit():
                max_num = max(max_num, int(hid[1:]))
        return f"H{max_num + 1:04d}"

    def init_voucher_state(self, household_id: str):
        """
        3B: 0/1 list for used status; index maps to voucher # (idx-1).
        """
        self.household_voucher_state[household_id] = {
            str(denom): [0] * count for denom, count in self.voucher_counts.items()
        }

    def ensure_voucher_state_for_all(self):
        """
        If households.csv has households missing in voucher_state.json, initialize them.
        """
        for hid in self.fin_to_household.values():
            if hid not in self.household_voucher_state:
                self.init_voucher_state(hid)

        # ---------- VoucherCode Format / Parse (for downstream redemption) ----------
    @staticmethod
    def format_voucher_code(household_id: str, denom: int, idx: int) -> str:
        """
        Deterministic, reversible voucher code.
        Example: V02-0001-H0001
        denom: 2/5/10
        idx: 1-based index within denom pool for the household
        """
        return f"V{denom:02d}-{idx:04d}-{household_id}"

    @staticmethod
    def parse_voucher_code(code: str) -> tuple[str, int, int]:
        """
        Reverse of format_voucher_code.
        Input: V02-0001-H0001
        Output: (household_id, denom, idx)
        """
        parts = code.strip().split("-")
        if len(parts) != 3 or not parts[0].startswith("V"):
            raise ValueError("Invalid voucher code format. Expected: V02-0001-H0001")

        denom = int(parts[0][1:])
        idx = int(parts[1])
        household_id = parts[2]
        return household_id, denom, idx
    
    # ---------- Main API for server ----------
    def register_household(self, fin_raw: str):
        """
        Main method you call from Flask.

        Returns:
            fin (normalized), household_id, already_registered (bool), error (str|None)
        """
        fin = self.normalize_fin(fin_raw)
        if not fin:
            return "", "", False, "FIN is required."

        # Existing
        if fin in self.fin_to_household:
            hid = self.fin_to_household[fin]
            already = True
            # Safety: ensure voucher state exists
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
