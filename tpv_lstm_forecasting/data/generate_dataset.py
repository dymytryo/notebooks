#!/usr/bin/env python3
"""Generate the synthetic dataset for the TPV LSTM forecasting case study.

Deterministic (seed 42): rerunning rewrites identical CSVs.

Daily payment operations for a virtual card program, January 2023 through
December 2025: payments issued, voided, and settled, with settled TPV (total
payment volume) as the forecasting target. The same program universe as the
merchant_retention and virtual_card_clv case studies, viewed at the daily
operational grain.

The structure a sequence model is supposed to learn is injected on purpose:

  - weekday funding pattern: Tuesday/Wednesday peak, thin weekends;
  - month-end crunch: AP (accounts payable) runs cluster in the last three
    business days and the first two of the next month, with larger invoices;
  - US holiday dips and a day-after catch-up;
  - compounding program growth, plus a permanent step-up in early 2024
    (the conversion campaign in the companion case studies);
  - settlement lag: net issuance settles 55/30/15 percent over the next
    one to three business days, and never on weekends, so Mondays spike;
  - void rate ~3 percent with an operational incident 2025-03-10..24
    (duplicate issuance bug) spiking it to ~10 percent;
  - multiplicative noise on everything.

Voids are recorded against their issue date (a simplification, most voids
land within a day or two); settlement is business-day realistic.
"""
from __future__ import annotations

import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
rng = random.Random(42)

START = date(2023, 1, 1)
END = date(2025, 12, 31)

BASE_COUNT = 1400.0                 # issued payments/business day at start
MONTHLY_GROWTH = 1.022
CAMPAIGN_STEP = {date(2024, 1, 15): 1.10, date(2024, 2, 15): 1.08}  # permanent lifts
AVG_PAYMENT = 1050.0
SIZE_DRIFT_MONTHLY = 1.0025

DOW_COUNT = {0: 1.00, 1: 1.18, 2: 1.16, 3: 1.05, 4: 0.92, 5: 0.15, 6: 0.08}
MONTH_END_COUNT = 1.45              # last 3 business days + first 2
MONTH_END_SIZE = 1.25
HOLIDAY_COUNT = 0.10
DAY_AFTER_HOLIDAY = 1.30

BASE_VOID = 0.032
INCIDENT_START = date(2025, 3, 10)   # duplicate-issuance bug: spike, then decay
INCIDENT_SPIKE = 0.095               # added to base at day 0
INCIDENT_HALFLIFE = 4.0              # days; ~two weeks visible

# Settlement lag is load-dependent (ops backlog): on heavy days the network
# and reconciliation queues push volume to later settlement days. Shares over
# the next 1..3 business days move with today's load vs the trailing level.
SETTLE_LIGHT = [0.58, 0.30, 0.12]    # load <= 1.0x trailing median
SETTLE_HEAVY = [0.38, 0.34, 0.28]    # load >= 1.5x trailing median

HOLIDAYS = {
    # fixed + observed US bank holidays, 2023-2025 (settlement-relevant subset)
    date(2023, 1, 2), date(2023, 1, 16), date(2023, 2, 20), date(2023, 5, 29),
    date(2023, 6, 19), date(2023, 7, 4), date(2023, 9, 4), date(2023, 10, 9),
    date(2023, 11, 23), date(2023, 12, 25),
    date(2024, 1, 1), date(2024, 1, 15), date(2024, 2, 19), date(2024, 5, 27),
    date(2024, 6, 19), date(2024, 7, 4), date(2024, 9, 2), date(2024, 10, 14),
    date(2024, 11, 28), date(2024, 12, 25),
    date(2025, 1, 1), date(2025, 1, 20), date(2025, 2, 17), date(2025, 5, 26),
    date(2025, 6, 19), date(2025, 7, 4), date(2025, 9, 1), date(2025, 10, 13),
    date(2025, 11, 27), date(2025, 12, 25),
}


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in HOLIDAYS


def next_business_days(d: date, n: int):
    out, cur = [], d
    while len(out) < n:
        cur += timedelta(days=1)
        if is_business_day(cur):
            out.append(cur)
    return out


def month_end_window(d: date) -> bool:
    """Last 3 business days of the month or first 2 of the month."""
    bds_fwd = [x for x in (d + timedelta(days=k) for k in range(1, 8))
               if x.month == d.month and is_business_day(x)]
    if is_business_day(d) and len(bds_fwd) < 3:
        return True
    bds_back = [x for x in (d - timedelta(days=k) for k in range(0, 4))
                if x.month == d.month and is_business_day(x)]
    return is_business_day(d) and d.day <= 4 and len(bds_back) <= 2


def main():
    days = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    growth, campaign = 1.0, 1.0
    trail = []                       # trailing net issuance for the load calc
    rows = {d: dict.fromkeys(
        ['issued_payments', 'issued_volume', 'voided_payments', 'voided_volume',
         'settled_payments', 'settled_volume'], 0.0) for d in days}
    extra = {}   # settlements landing after END are dropped; before START ignored

    for d in days:
        if d.day == 1:
            growth *= MONTHLY_GROWTH
        if d in CAMPAIGN_STEP:
            campaign *= CAMPAIGN_STEP[d]

        mult = DOW_COUNT[d.weekday()]
        if d in HOLIDAYS:
            mult *= HOLIDAY_COUNT
        prev = d - timedelta(days=1)
        if prev in HOLIDAYS and is_business_day(d):
            mult *= DAY_AFTER_HOLIDAY
        if month_end_window(d):
            mult *= MONTH_END_COUNT

        # weekday amplitude breathes with the season (flatter summers)
        season_amp = 1 + 0.06 * math.sin(2 * math.pi * (d.month - 1) / 12)
        mult = 1 + (mult - 1) * season_amp

        count = BASE_COUNT * growth * campaign * mult * rng.lognormvariate(0, 0.06)
        months_in = (d.year - START.year) * 12 + d.month - START.month
        size = AVG_PAYMENT * (SIZE_DRIFT_MONTHLY ** months_in) * rng.lognormvariate(0, 0.04)
        if month_end_window(d):
            # the crunch premium grows with program scale (bigger AP runs batch harder)
            size *= 1.10 + 0.18 * min(growth, 2.2) / 2.2
        issued_volume = count * size

        void_rate = BASE_VOID
        if d >= INCIDENT_START:
            void_rate += INCIDENT_SPIKE * math.exp(-((d - INCIDENT_START).days) / INCIDENT_HALFLIFE)
        void_rate *= rng.lognormvariate(0, 0.10)
        voided_volume = issued_volume * void_rate
        net = issued_volume - voided_volume

        r = rows[d]
        r['issued_payments'] = round(count)
        r['issued_volume'] = round(issued_volume, 2)
        r['voided_payments'] = round(count * void_rate)
        r['voided_volume'] = round(voided_volume, 2)

        # load vs trailing level decides how fast today's net settles
        trail.append(net)
        if len(trail) > 20:
            trail.pop(0)
        level = sorted(trail)[len(trail) // 2]
        load = min(max(net / level, 0.6), 1.5) if level else 1.0
        w = (load - 1.0) / 0.5 if load > 1.0 else 0.0     # 0 at <=1.0x, 1 at 1.5x
        shares = [l + (h - l) * w for l, h in zip(SETTLE_LIGHT, SETTLE_HEAVY)]

        for share, sd in zip(shares, next_business_days(d, 3)):
            amt = net * share * rng.lognormvariate(0, 0.015)
            cnt = (r['issued_payments'] - r['voided_payments']) * share
            if sd in rows:
                rows[sd]['settled_volume'] += amt
                rows[sd]['settled_payments'] += cnt

    with open(HERE / 'daily_payments.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'issued_payments', 'issued_volume', 'voided_payments',
                    'voided_volume', 'settled_payments', 'settled_volume'])
        for d in days:
            r = rows[d]
            w.writerow([d.isoformat(), int(r['issued_payments']), r['issued_volume'],
                        int(r['voided_payments']), r['voided_volume'],
                        int(round(r['settled_payments'])), round(r['settled_volume'], 2)])

    total = sum(rows[d]['settled_volume'] for d in days)
    print(f'{len(days)} days | settled TPV ${total/1e9:,.2f}B | '
          f'first {days[0]} last {days[-1]}')


if __name__ == '__main__':
    main()
