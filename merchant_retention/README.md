# Merchant Retention for a Virtual Card Program

The North Star Metric (NSM) for a payments program converting merchants from
paper check to a single-use account (SUA) virtual card: the share of SUA
volume retained over a 3-month window, with the enrollment base reported
alongside it. Rebuilt in SQL from the 2022 production analysis, which ran on
Amazon Athena, modeled with dbt, and published to QuickSight.

## What the Notebook Does

1. **Turns change data capture (CDC) into enrollment history** — deduplicates
   a field-level change log (the loader replayed files), pairs each join with
   its following churn, unions in a churn batch applied by a manual ETL that
   never hit the log, and fills open intervals with the anchor date.
2. **Reports monthly program movement** — beginning-of-month, joined,
   churned, end-of-month counts. The chart reads as an audit trail: an
   outreach campaign spikes joins (+256, +331), its wrongful conversions
   revert the next month (208 churns), a manual batch steps the curve in
   June.
3. **Builds the marts first** — `payment_detail_agg` and
   `merchant_retention_record`, the dbt move that got the production version
   under Athena's 100 GB per-query scan cap and made the metric
   self-serviceable.
4. **Computes the North Star with plain joins** — replacing the original
   Presto `map_agg` / `array_intersect` / `reduce` single-pass algebra, kept
   in the notebook as an exhibit of what aged out.
5. **Separates two retention lenses** — *activity* (transacted in M-3 and M)
   vs *enrollment* (still on the payment method). Occasionally paid merchants
   retain the method best (92.0%) while looking churny on activity (51.1%)
   because they simply skip months; high-frequency merchants revert the most
   (65.3%), since interchange and reconciliation costs compound weekly.

## Headline Numbers

| Metric (3-month window, period average) | Value |
|---|---|
| Enrollment retention (still on SUA) | 86.5% |
| Retained volume share — the North Star | 73.0% |
| Activity retention (transacted M-3 and M) | 69.9% |

Validation recovers the generator's ground truth exactly: 2,614 enrollment
stints, 1,418 still enrolled, 45 manual churns recovered, 66 re-joins,
0 overlapping enrollments.

## Files

- [`merchant_retention.ipynb`](merchant_retention.ipynb) — the analysis,
  executed end-to-end on the bundled data. No credentials or network needed.
- [`data/change_log.csv`](data/change_log.csv),
  [`data/payments.csv`](data/payments.csv),
  [`data/merchants.csv`](data/merchants.csv),
  [`data/ops_manual_updates.csv`](data/ops_manual_updates.csv) —
  **synthetic**, deterministic (seed 42). Duplicate CDC rows, the off-log
  churn batch, the campaign spike, and segment-dependent churn are all
  injected on purpose and documented in
  [`data/generate_transactions.py`](data/generate_transactions.py).

## Run It

```bash
pip install duckdb pandas matplotlib jupyter
jupyter notebook merchant_retention.ipynb   # runs top to bottom
python data/generate_transactions.py        # rebuilds data/ byte-identically
```

## What Aged Out

The 2022 original queried the raw change log per report under Athena's scan
cap, which forced the Presto map/array gymnastics, and published to
QuickSight. The marts pattern is the part that survives: model once with
dbt, then any BI tool and any analyst can read the metric off small tables
with boring joins.
