"""Deterministic sample generator for the supply chain exploration notebook.

Draws a ~5% customer sample from the original (private) extracts while
preserving the properties the notebook's data-quality checks depend on:

- **Full history per customer** — sampling happens at the customer level
  (``hash(customer_id) % 20 == 0``), never at the row level, so retention
  cohorts and year-over-year comparisons stay coherent.
- **Referential quirks survive** — customer_ids that appear in FILES but not
  in CUSTOMERS (and customers with no shipments at all) are sampled with the
  same rule, so the notebook's orphan checks still find what they found on
  the full data.
- **Containers follow their shipments** — every container row whose
  global_file_id belongs to a sampled shipment is kept.

The full extracts are not distributable (FILES.csv alone is 146 MB, above
GitHub's 100 MB limit). Point ``SOURCE_DIR`` at a folder containing the
original FILES.csv / CONTAINERS.csv / CUSTOMERS.csv to regenerate.

Usage:
    SOURCE_DIR=/path/to/full/extracts python make_sample.py
"""

import os

import duckdb

SOURCE_DIR = os.environ.get("SOURCE_DIR", ".")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

con = duckdb.connect()
for t in ("FILES", "CONTAINERS", "CUSTOMERS"):
    con.execute(
        f"CREATE VIEW {t.lower()} AS SELECT * FROM read_csv_auto('{SOURCE_DIR}/{t}.csv')"
    )

# ~5% of customers that have shipments, chosen by stable hash (no RNG state).
con.execute(
    """
    CREATE TABLE sampled_customers AS
    SELECT DISTINCT customer_id FROM files WHERE hash(customer_id) % 20 = 0
    """
)

con.execute(
    f"""
    COPY (SELECT f.* FROM files f JOIN sampled_customers USING (customer_id))
    TO '{OUT_DIR}/FILES.csv' (HEADER)
    """
)
con.execute(
    f"""
    COPY (
        SELECT c.* FROM containers c
        WHERE c.global_file_id IN (
            SELECT global_file_id FROM files f JOIN sampled_customers USING (customer_id)
        )
    ) TO '{OUT_DIR}/CONTAINERS.csv' (HEADER)
    """
)
con.execute(
    f"""
    COPY (
        SELECT c.* FROM customers c JOIN sampled_customers USING (customer_id)
        UNION ALL
        SELECT c.* FROM customers c
        WHERE c.customer_id NOT IN (SELECT DISTINCT customer_id FROM files)
          AND hash(c.customer_id) % 20 = 0
    ) TO '{OUT_DIR}/CUSTOMERS.csv' (HEADER)
    """
)

print("Sample written to", OUT_DIR)
