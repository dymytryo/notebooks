"""Generate a synthetic stand-in for the original opportunity dataset.

The real analysis ran against per-cluster merchant opportunity amounts pulled
from the warehouse. That data cannot be published, so this script produces a
statistically similar synthetic sample: log-normally distributed transaction
amounts (typical for B2B payment sizes) across a handful of lead clusters.

Run once to (re)create ``opportunity_per_cluster_sample.csv``:

    python generate_sample_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)
N_ROWS = 55_000
OUT_PATH = Path(__file__).resolve().with_name("opportunity_per_cluster_sample.csv")

cluster_id = RNG.integers(1, 9, size=N_ROWS)

# Log-normal amounts: median ≈ $1,000, long right tail capped at $250K,
# floored at $25 to avoid unrealistically small invoices.
amount = RNG.lognormal(mean=6.9, sigma=1.1, size=N_ROWS)
amount = amount.clip(25, 250_000).round(2)

df = pd.DataFrame({"cluster_id": cluster_id, "amount": amount})
df.to_csv(OUT_PATH, index=False)

print(f"Wrote {len(df):,} rows to {OUT_PATH}")
print(df["amount"].describe())
