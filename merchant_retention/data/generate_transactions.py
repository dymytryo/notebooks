#!/usr/bin/env python3
"""Generate the synthetic dataset for the merchant retention case study.

Deterministic (seed 42): rerunning rewrites identical CSVs.

Models a payments program converting merchants from paper check to a
single-use account (SUA) virtual card, January 2022 through December 2023,
with the analysis anchored at 2024-01-01. The quirks the analysis has to
survive are injected on purpose:

  change_log.csv        field-level change data capture (CDC) of merchant
                        attributes. ~3% exact duplicate rows (the reason the
                        original SQL ranks before pairing), plus unrelated
                        subscription_type changes as noise.
  ops_manual_updates.csv a batch of merchants force-churned by a manual
                        backfill on 2023-06-06 that never hit the change
                        log; the analysis must union it in or overstate
                        end-of-month counts from that date on.
  payments.csv          SUA payments while enrolled. Payment frequency and
                        volume differ by segment, which is what makes the
                        activity-based and enrollment-based retention
                        lenses disagree.
  merchants.csv         merchant directory with payer and channel_source.

Story beats the charts should surface:
  - steady program growth through 2022;
  - an outreach campaign spikes joins in 2023-01/02, and ~30% of those
    conversions were wrongful and revert in 2023-03;
  - a manual churn batch steps the curve down on 2023-06-06;
  - occasional merchants retain the payment method best (they rarely eat
    interchange), high-frequency merchants revert the most;
  - transactable volume keeps growing even where retention sags, because
    acquisition outpaces churn.
"""
from __future__ import annotations

import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = random.Random(42)

START = date(2021, 6, 1)            # first joins
PAY_START = date(2022, 1, 1)        # payments window
END = date(2023, 12, 31)
AS_OF = date(2024, 1, 1)

SUA = "Credit Card"                 # the single-use account (SUA) virtual card
OTHER_METHODS = ["Check", "ACH", "Wire"]
CHANNELS = [16, 26, 30]

SEGMENTS = {
    #  name            share  pays/month  monthly churn hazard  volume $/payment
    "occasional":     (0.45,  0.55,       0.020,  (250, 1_400)),
    "regular":        (0.35,  1.20,       0.045,  (1_200, 6_500)),
    "high_frequency": (0.20,  4.50,       0.120,  (3_500, 16_000)),
}

CAMPAIGN = {date(2023, 1, 1): 180, date(2023, 2, 1): 260}
WRONGFUL_SHARE = 0.30               # campaign joins reverted in 2023-03
MANUAL_BATCH_DATE = date(2023, 6, 6)
MANUAL_BATCH_SIZE = 45
REJOIN_SHARE = 0.06                 # churned merchants who later rejoin


def months(start: date, end: date):
    d = start.replace(day=1)
    while d <= end:
        yield d
        d = (d + timedelta(days=32)).replace(day=1)


def month_len(d: date) -> int:
    nxt = (d + timedelta(days=32)).replace(day=1)
    return (nxt - d).days


def pick_segment() -> str:
    roll, acc = rng.random(), 0.0
    for name, (share, *_rest) in SEGMENTS.items():
        acc += share
        if roll < acc:
            return name
    return "high_frequency"


def main() -> None:
    merchants = []          # merchant_id, payer_id, segment, channel_source
    stints = []             # merchant_id, join_date, churn_date|None, wrongful, manual
    seq = 0

    # --- enrollment waves -------------------------------------------------
    for m0 in months(START, END):
        base = 55 + int((m0 - START).days / 30 * 0.9)     # slow growth
        joins = base + rng.randint(-8, 8) + CAMPAIGN.get(m0, 0)
        campaign_join = CAMPAIGN.get(m0, 0) > 0
        for _ in range(joins):
            seq += 1
            mid = f"mid{seq:05d}"
            segment = pick_segment()
            merchants.append({
                "merchant_id": mid,
                "payer_id": f"pid{rng.randint(1, 700):04d}",
                "segment": segment,
                "channel_source": rng.choice(CHANNELS),
            })
            join_day = m0 + timedelta(days=rng.randint(0, month_len(m0) - 1))
            is_wrongful = campaign_join and rng.random() < WRONGFUL_SHARE
            stints.append({
                "merchant_id": mid, "segment": segment,
                "join_date": join_day, "churn_date": None,
                "wrongful": is_wrongful, "manual": False,
            })

    # --- churn: hazard per month, wrongful reversals, manual batch --------
    manual_pool = []
    for s in stints:
        if s["wrongful"]:
            s["churn_date"] = date(2023, 3, rng.randint(2, 26))
            continue
        hazard = SEGMENTS[s["segment"]][2]
        d = (s["join_date"] + timedelta(days=32)).replace(day=1)
        while d <= END:
            if rng.random() < hazard:
                s["churn_date"] = d + timedelta(days=rng.randint(0, month_len(d) - 1))
                break
            d = (d + timedelta(days=32)).replace(day=1)
        if (s["churn_date"] is None and s["join_date"] < date(2023, 4, 1)
                and len(manual_pool) < MANUAL_BATCH_SIZE * 3):
            manual_pool.append(s)

    manual_batch = rng.sample(manual_pool, MANUAL_BATCH_SIZE)
    for s in manual_batch:
        s["churn_date"] = MANUAL_BATCH_DATE
        s["manual"] = True

    # --- rejoins (exercise the join->churn pairing) -----------------------
    rejoins = []
    for s in stints:
        if (s["churn_date"] and not s["manual"] and rng.random() < REJOIN_SHARE
                and s["churn_date"] < date(2023, 9, 1)):
            back = s["churn_date"] + timedelta(days=rng.randint(45, 160))
            if back <= END:
                rejoins.append({
                    "merchant_id": s["merchant_id"], "segment": s["segment"],
                    "join_date": back, "churn_date": None,
                    "wrongful": False, "manual": False,
                })
    for s in rejoins:                       # second stint may churn again
        hazard = SEGMENTS[s["segment"]][2]
        d = (s["join_date"] + timedelta(days=32)).replace(day=1)
        while d <= END:
            if rng.random() < hazard:
                s["churn_date"] = d + timedelta(days=rng.randint(0, month_len(d) - 1))
                break
            d = (d + timedelta(days=32)).replace(day=1)
    stints.extend(rejoins)
    stints.sort(key=lambda s: (s["merchant_id"], s["join_date"]))

    # --- change log --------------------------------------------------------
    payer_of = {m["merchant_id"]: m["payer_id"] for m in merchants}
    log = []
    for s in stints:
        prev = rng.choice(OTHER_METHODS)
        log.append((datetime.combine(s["join_date"], datetime.min.time())
                    + timedelta(hours=rng.randint(8, 20), minutes=rng.randint(0, 59)),
                    payer_of[s["merchant_id"]], "payment_method",
                    s["merchant_id"], prev, SUA))
        if s["churn_date"] and not s["manual"]:
            log.append((datetime.combine(s["churn_date"], datetime.min.time())
                        + timedelta(hours=rng.randint(8, 20), minutes=rng.randint(0, 59)),
                        payer_of[s["merchant_id"]], "payment_method",
                        s["merchant_id"], SUA, rng.choice(OTHER_METHODS)))
    # unrelated field changes: noise the WHERE clause must exclude
    all_mids = [m["merchant_id"] for m in merchants]
    for _ in range(1200):
        mid = rng.choice(all_mids)
        d = START + timedelta(days=rng.randint(0, (END - START).days))
        log.append((datetime.combine(d, datetime.min.time())
                    + timedelta(hours=rng.randint(0, 23)),
                    payer_of[mid], "subscription_type", mid,
                    str(rng.randint(1, 11)), str(rng.randint(1, 11))))
    # exact duplicates (~3%): the loader occasionally replays a file
    log.extend(rng.sample(log, int(len(log) * 0.03)))
    log.sort(key=lambda r: (r[0], r[3], r[2], r[4], r[5]))

    # --- payments -----------------------------------------------------------
    payments, pay_seq = [], 0
    for s in stints:
        _share, per_month, _hz, (lo, hi) = SEGMENTS[s["segment"]]
        churn = s["churn_date"] or AS_OF
        for m0 in months(max(s["join_date"], PAY_START), END):
            n, frac = int(per_month), per_month - int(per_month)
            if rng.random() < frac:
                n += 1
            for _ in range(n):
                pay_day = m0 + timedelta(days=rng.randint(0, month_len(m0) - 1))
                if not (s["join_date"] <= pay_day < churn) or pay_day < PAY_START:
                    continue          # only while enrolled, only in-window
                pay_seq += 1
                payments.append((
                    f"txn{pay_seq:07d}", s["merchant_id"],
                    payer_of[s["merchant_id"]], str(pay_day),
                    f"{rng.uniform(lo, hi):.2f}", SUA,
                ))
    payments.sort(key=lambda r: (r[3], r[1], r[0]))

    # --- write --------------------------------------------------------------
    def write(name, header, rows):
        with open(HERE / name, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
        print(f"  data/{name}: {len(rows)} rows")

    write("merchants.csv",
          ["merchant_id", "payer_id", "segment", "channel_source"],
          [[m["merchant_id"], m["payer_id"], m["segment"], m["channel_source"]]
           for m in sorted(merchants, key=lambda m: m["merchant_id"])])
    write("change_log.csv",
          ["change_date", "payer_id", "record_type", "entity_id",
           "val_prev", "val_curr"],
          [[r[0].strftime("%Y-%m-%d %H:%M:%S"), r[1], r[2], r[3], r[4], r[5]]
           for r in log])
    write("ops_manual_updates.csv",
          ["entity_id", "churn_date", "note"],
          [[s["merchant_id"], str(MANUAL_BATCH_DATE), "manual ETL backfill"]
           for s in sorted(manual_batch, key=lambda s: s["merchant_id"])])
    write("payments.csv",
          ["transaction_id", "merchant_id", "payer_id", "paid_at",
           "amount_usd", "payment_method"],
          payments)

    # ground truth for the notebook's validation cell
    n_stints = len(stints)
    n_open = sum(1 for s in stints if s["churn_date"] is None)
    print(f"  ground truth: {n_stints} stints, {n_open} open, "
          f"{len(manual_batch)} manual churns, "
          f"{sum(1 for s in stints if s['wrongful'])} wrongful conversions, "
          f"{len(rejoins)} rejoins")


if __name__ == "__main__":
    main()
