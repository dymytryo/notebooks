"""Generate a synthetic merchant-contact extract with deliberate quality issues.

The point of this dataset is to be messy on purpose. It simulates a raw
contact-list drop from an upstream CRM — the kind of file you profile BEFORE
letting it anywhere near the warehouse. Every defect is injected knowingly:

- missing values at different rates per column;
- exact duplicate rows and fuzzy duplicates (name/case variants of the same
  merchant);
- four different phone number formats in one column;
- ZIP codes that lost their leading zero on the way through a spreadsheet;
- inconsistent state codes (case variants plus a few invalid ones);
- status labels with mixed casing;
- sentinel dates (1900-01-01) and a few future signup dates;
- monthly volume with negatives, zeros, and one absurd outlier.

All names, companies, and contact details are fabricated.

Run once to (re)create ``merchant_contacts_raw.csv``:

    python generate_sample_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(7)
N = 2000
OUT_PATH = Path(__file__).resolve().with_name("merchant_contacts_raw.csv")

FIRST = ["James", "Maria", "Robert", "Linda", "Michael", "Sarah", "David",
         "Karen", "Daniel", "Nancy", "Kevin", "Laura", "Brian", "Emma",
         "Jason", "Olivia", "Mark", "Sophia", "Paul", "Anna"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
        "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor",
        "Thomas", "Moore", "Jackson", "Martin", "Lee", "Walker", "Hall"]
COMPANY_A = ["Summit", "Cedar", "Lakeside", "Ironwood", "Bluebird", "Harbor",
             "Redstone", "Prairie", "Copper", "Willow", "Granite", "Pioneer"]
COMPANY_B = ["Plumbing", "Logistics", "Catering", "Roofing", "Consulting",
             "Landscaping", "Electric", "Printing", "Bakery", "Auto Repair",
             "HVAC", "Cleaning"]
CITIES = [("Houston", "TX", "77002"), ("Spring", "TX", "77373"),
          ("Boston", "MA", "02108"), ("Providence", "RI", "02903"),
          ("Chicago", "IL", "60601"), ("Denver", "CO", "80202"),
          ("Portland", "OR", "97201"), ("Newark", "NJ", "07102"),
          ("Phoenix", "AZ", "85001"), ("Atlanta", "GA", "30303")]
STATUS_CLEAN = ["active", "churned", "pending"]


def phone(rng):
    a, b, c = rng.integers(200, 999), rng.integers(200, 999), rng.integers(1000, 9999)
    style = rng.integers(0, 4)
    if style == 0:
        return f"({a}) {b}-{c}"
    if style == 1:
        return f"{a}-{b}-{c}"
    if style == 2:
        return f"{a}{b}{c}"
    return f"+1 {a} {b} {c}"


rows = []
for i in range(N):
    first = FIRST[RNG.integers(0, len(FIRST))]
    last = LAST[RNG.integers(0, len(LAST))]
    company = f"{COMPANY_A[RNG.integers(0, len(COMPANY_A))]} {COMPANY_B[RNG.integers(0, len(COMPANY_B))]}"
    city, state, zipc = CITIES[RNG.integers(0, len(CITIES))]

    # inconsistent state casing + a few invalid codes
    r = RNG.random()
    if r < 0.06:
        state = state.lower()
    elif r < 0.08:
        state = {"TX": "Tex", "MA": "Mass", "IL": "Ill."}.get(state, state)

    # ZIPs that lost their leading zero in a spreadsheet
    if zipc.startswith("0") and RNG.random() < 0.55:
        zipc = zipc.lstrip("0")

    status = STATUS_CLEAN[RNG.integers(0, 3)]
    if RNG.random() < 0.18:
        status = status.upper() if RNG.random() < 0.5 else status.title()

    signup = pd.Timestamp("2019-01-01") + pd.Timedelta(days=int(RNG.integers(0, 2500)))
    if RNG.random() < 0.015:
        signup = pd.Timestamp("1900-01-01")          # sentinel
    elif RNG.random() < 0.008:
        signup = pd.Timestamp("2031-05-14")          # future date

    volume = float(np.round(RNG.lognormal(7.4, 1.2), 2))
    r = RNG.random()
    if r < 0.01:
        volume = 0.0
    elif r < 0.018:
        volume = -volume                              # refund rows leaked in

    rows.append({
        "record_id": f"MRC-{100000 + i}",
        "company_name": company,
        "contact_first": first,
        "contact_last": last,
        "email": f"{first.lower()}.{last.lower()}@{company.split()[0].lower()}-example.com",
        "phone": phone(RNG),
        "city": city,
        "state": state,
        "zip": zipc,
        "signup_date": signup.date().isoformat(),
        "monthly_volume": volume,
        "status": status,
    })

df = pd.DataFrame(rows)

# one absurd outlier
df.loc[df.index[500], "monthly_volume"] = 1.2e9

# missingness at different rates per column
for col, rate in [("contact_first", 0.08), ("phone", 0.12), ("zip", 0.05),
                  ("email", 0.03), ("signup_date", 0.02)]:
    idx = RNG.random(len(df)) < rate
    df.loc[idx, col] = np.nan

# exact duplicates
exact = df.sample(n=12, random_state=11)
df = pd.concat([df, exact], ignore_index=True)

# fuzzy duplicates: same merchant, name typed differently
fuzz = df.sample(n=48, random_state=13).copy()
fuzz["record_id"] = [f"MRC-{200000 + i}" for i in range(len(fuzz))]
fuzz["contact_first"] = fuzz["contact_first"].str.upper()
fuzz["company_name"] = fuzz["company_name"].str.upper()
df = pd.concat([df, fuzz], ignore_index=True)

df = df.sample(frac=1, random_state=17).reset_index(drop=True)
df.to_csv(OUT_PATH, index=False)

print(f"Wrote {len(df):,} rows to {OUT_PATH}")
print("nulls per column:\n", df.isna().sum())
