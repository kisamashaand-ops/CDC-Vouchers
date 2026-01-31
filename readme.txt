
# Household Registration Module

This module implements **Household Account Registration** for the CDC Voucher System.

## Files

server.py  
Flask web server providing registration UI and API.

data_structure.py  
Core logic implemented using OOP.  
Contains `HouseholdRegistry` class handling:
- FIN → Household_ID mapping
- Household_ID incremental assignment (H0001, H0002, …)
- Voucher pool initialization
- Data persistence

templates/
- household_register.html : FIN input page  
- household_regi_result.html : Registration result page  

data/
- households.csv : FIN ↔ Household_ID mapping table  
- voucher_state.json : Voucher usage state per household  

---

## Registration Flow

Input: FIN Number  
If FIN already exists → return existing Household_ID  
If FIN new → assign next Household_ID and initialize voucher pool.

Output: Household_ID displayed on result page.

---

## Persistent Data Output

### households.csv
Stores one-to-one mapping:
FIN,Household_ID
G1234567X,H0001


### voucher_state.json
Stores voucher usage flags (0 = unused, 1 = used):
```json
{
  "H0001": {
    "2": [0,...],   // 80 entries
    "5": [0,...],   // 32 entries
    "10":[0,...]    // 45 entries
  }
}

### Voucher Uniqueness Design

Each voucher is uniquely identified by the triple:(household_id, denom, idx)
- household_id : Household ID
- denom : voucher denomination (2 / 5 / 10)
- idx : serial number within that denomination pool
This triple maps one-to-one to a specific position in voucher_state.json.

### Voucher Code Rule (for downstream redemption)

Voucher codes are deterministic and reversible:
HouseholdRegistry.format_voucher_code(household_id, denom, idx)
# Example: V02-0042-H0001
HouseholdRegistry.parse_voucher_code(voucher_code)
# Returns: (household_id, denom, idx)
Downstream redemption locates a specific voucher via:voucher_state[household_id][str(denom)][idx-1]


An API can be added later to display the vouchers corresponding to the household_ID.
