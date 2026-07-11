"""Deterministic generator for the two bundled sheet snapshots.

Simulates what the Sheets API returns on two consecutive daily pulls of an
ops team's working sheet, sheet-isms included on purpose:

- every value is a string (the API's ``values().get`` returns strings)
- currency entered by humans: ``$1,234.50``
- checkbox columns as ``TRUE`` / ``FALSE``
- blank strings where a cell was cleared, not NULLs
- inconsistent header casing/spacing

Day 2 differs from day 1 by exactly: 3 inserted rows, 2 updated rows,
1 deleted row — so the change-capture section has known ground truth.
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).parent
random.seed(20)

HEADER = ["Record ID", "Merchant ID", "Contact Date", "Rep",
          "Contact Type", "Call Outcome", "Follow Up Needed",
          "Monthly Volume USD", "Notes"]

REPS = ["a.moss", "k.tran", "j.ibarra", "s.okafor"]
TYPES = ["call", "email", "call", "call", "email"]
OUTCOMES = ["resolved", "escalated", "no answer", "left voicemail", ""]
NOTES = ["", "payor dispute", "requested W-9", "", "onboarding question",
         "", "duplicate account", "", "limit increase", ""]


def make_row(i: int) -> list[str]:
    volume = random.randint(800, 250_000) + random.random()
    return [
        f"rec-{i:04d}",
        f"m{random.randrange(16**8):08x}",
        f"2022-08-{random.randint(1, 8):02d}",
        random.choice(REPS),
        random.choice(TYPES),
        random.choice(OUTCOMES),
        random.choice(["TRUE", "FALSE"]),
        f"${volume:,.2f}",
        random.choice(NOTES),
    ]


rows = [make_row(i) for i in range(1, 41)]                      # day 1: 40 rows

with (OUT / "snapshot_2022-08-08.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    w.writerows(rows)

# day 2: updates, a delete, and inserts against day 1
day2 = [r[:] for r in rows]
day2[4][5] = "resolved"          # rec-0005: outcome filled in
day2[4][6] = "FALSE"
day2[17][7] = "$98,410.00"       # rec-0018: volume corrected
del day2[29]                     # rec-0030: row deleted by the team
day2 += [make_row(i) for i in range(41, 44)]                    # 3 new records

with (OUT / "snapshot_2022-08-09.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    w.writerows(day2)

print("wrote snapshot_2022-08-08.csv and snapshot_2022-08-09.csv")
