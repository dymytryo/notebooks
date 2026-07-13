#!/usr/bin/env python3
"""Generate the synthetic dataset for the virtual card CLV case study.

Deterministic (seed 42): rerunning rewrites identical CSVs.

Models the value side of a payments program converting merchants from
check and ACH (automated clearing house) to a virtual card rail, January
2023 through December 2025, with the analysis anchored at 2026-01-01.
Enrollment history arrives already reconciled (the companion
merchant_retention study covers how it is rebuilt from change data
capture); this dataset is about how much a converted merchant is worth
and how long they stay on the rail.

  merchants.csv    one row per converted merchant: segment, prior rail,
                   onboarding channel, conversion month, churn month
                   (empty while still enrolled at the anchor date).
  vc_payments.csv  monthly grain, active months only: payment count and
                   settled volume while enrolled. Enrolled months with no
                   payments simply have no row, which is what makes
                   recency a real feature and MAPE a broken metric here.

Behavior injected on purpose, so the charts have something to find:
  - churn hazard differs by segment: high_frequency merchants pay the
    most but revert the most (interchange and reconciliation costs
    compound weekly); occasional merchants keep the rail and just skip
    months;
  - the first three months on the rail carry a hazard shock (the
    reconciliation-friction discovery window), and merchants past a year
    get sticky;
  - onboarding channel matters: integrated (AP-platform API) converts
    retain far better than outreach converts;
  - ACH converts churn back more easily than check converts (the rail
    upgrade was smaller to begin with);
  - an outreach campaign spikes conversions in 2024-01/02 and those
    cohorts retain visibly worse, which the retention heatmap should
    show as two weak rows;
  - mild volume growth and a Nov/Dec seasonality bump.
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = random.Random(42)

FIRST_COHORT = (2023, 1)
LAST_COHORT = (2025, 12)
LAST_OBSERVED = (2025, 12)          # analysis anchored at 2026-01-01

NET_TAKE = 0.010                    # program net revenue as a share of volume
                                    # (2.5% interchange x 40% program share),
                                    # applied in the notebook, documented here

#  name              share  pays/mo  base hazard  payment size (mu, sigma of ln $)
SEGMENTS = {
    "occasional":     (0.45, 0.55,   0.020,       (6.55, 0.55)),   # ~$800
    "regular":        (0.35, 1.30,   0.045,       (7.90, 0.50)),   # ~$3,000
    "high_frequency": (0.20, 4.50,   0.085,       (8.90, 0.45)),   # ~$8,100
}
CHANNELS = {"outreach": (0.40, 1.35), "organic": (0.35, 1.00), "integrated": (0.25, 0.55)}
PRIOR_RAILS = {"Check": (0.60, 1.00), "ACH": (0.40, 1.15)}

CAMPAIGN_COHORTS = {(2024, 1): 180, (2024, 2): 230}   # extra outreach conversions
CAMPAIGN_EXTRA_HAZARD = 1.30                          # and they are shakier

BASE_CONVERSIONS = 55               # per month, growing ~3% monthly
MONTHLY_GROWTH = 1.03
SIZE_DRIFT = 1.003                  # payment size drift per calendar month
SEASONAL = {11: 1.20, 12: 1.20, 7: 0.90}


def month_seq(start, end):
    y, m = start
    while (y, m) <= end:
        yield (y, m)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def month_index(ym):
    return ym[0] * 12 + ym[1] - 1


def add_months(ym, k):
    i = month_index(ym) + k
    return (i // 12, i % 12 + 1)


def fmt(ym):
    return f"{ym[0]:04d}-{ym[1]:02d}-01"


def pick(weighted):
    r, acc = rng.random(), 0.0
    for name, w in weighted:
        acc += w
        if r <= acc:
            return name
    return weighted[-1][0]


def poisson(lam):
    # Knuth's algorithm; lambda is small here
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def tenure_multiplier(tenure):
    if tenure <= 3:
        return 1.80
    if tenure <= 12:
        return 1.00
    return 0.70


def main():
    merchants, payments = [], []
    mid = 10000

    for cohort in month_seq(FIRST_COHORT, LAST_COHORT):
        k = month_index(cohort) - month_index(FIRST_COHORT)
        n = round(BASE_CONVERSIONS * MONTHLY_GROWTH ** k)
        extra = CAMPAIGN_COHORTS.get(cohort, 0)

        for j in range(n + extra):
            mid += 1
            campaign = j >= n                       # the spike is outreach-sourced
            segment = pick([(s, w[0]) for s, w in SEGMENTS.items()])
            channel = "outreach" if campaign else pick([(c, w[0]) for c, w in CHANNELS.items()])
            prior = pick([(p, w[0]) for p, w in PRIOR_RAILS.items()])

            _, pays_mo, base_hazard, (mu, sigma) = SEGMENTS[segment]
            hazard = (base_hazard * CHANNELS[channel][1] * PRIOR_RAILS[prior][1]
                      * (CAMPAIGN_EXTRA_HAZARD if campaign else 1.0))

            # walk the merchant month by month until churn or the anchor
            churn = None
            active_months = []
            for tenure, ym in enumerate(month_seq(cohort, LAST_OBSERVED), start=1):
                if rng.random() < min(hazard * tenure_multiplier(tenure), 0.60):
                    churn = ym
                    break
                season = SEASONAL.get(ym[1], 1.0)
                n_pays = poisson(pays_mo * season)
                if n_pays > 0:
                    drift = SIZE_DRIFT ** (month_index(ym) - month_index(FIRST_COHORT))
                    volume = sum(rng.lognormvariate(mu, sigma) for _ in range(n_pays)) * drift
                    active_months.append((ym, n_pays, round(volume, 2)))

            merchants.append({
                "merchant_id": f"M{mid}",
                "segment": segment,
                "converted_from": prior,
                "onboarding_channel": channel,
                "conversion_month": fmt(cohort),
                "churn_month": fmt(churn) if churn else "",
            })
            for ym, n_pays, volume in active_months:
                payments.append({
                    "merchant_id": f"M{mid}",
                    "month": fmt(ym),
                    "payments": n_pays,
                    "volume": volume,
                })

    payments.sort(key=lambda r: (r["month"], r["merchant_id"]))

    with open(HERE / "merchants.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(merchants[0]))
        w.writeheader()
        w.writerows(merchants)
    with open(HERE / "vc_payments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(payments[0]))
        w.writeheader()
        w.writerows(payments)

    enrolled = sum(1 for m in merchants if not m["churn_month"])
    print(f"{len(merchants)} merchants | {enrolled} still enrolled | {len(payments)} monthly payment rows")


if __name__ == "__main__":
    main()
