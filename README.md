# Notebook Portfolio

Cleaned Jupyter analyses and small notebook-backed case studies.

## Case Studies

- [`monte_carlo_revenue_simulation/`](monte_carlo_revenue_simulation/) -
  campaign revenue simulation with 10,000-trial outcome distributions.
- [`data_profiling/`](data_profiling/) - automated source-file profiling before
  warehouse ingestion.
- [`loan_amortization/`](loan_amortization/) - fixed-rate amortization and
  early-principal payoff scenario modeling.
- [`supply_chain_exploration/`](supply_chain_exploration/) - freight-forwarding
  EDA in DuckDB: SQL profiling, key forensics, one-big-table assembly, lasso
  revenue-driver decomposition, margin and retention analysis.
- [`gsheets_ingestion/`](gsheets_ingestion/) - self-serve Google Sheets
  ingestion: typed normalization of API pulls and change capture (inserts,
  updates, deletes) via snapshot diffing, landed as Parquet for dbt.
- [`merchant_retention/`](merchant_retention/) - North Star Metric for a
  virtual card program: CDC change log to enrollment history, dbt-style
  marts, and 3-month cohort retention in SQL, with activity vs enrollment
  lenses separated.
- [`virtual_card_clv/`](virtual_card_clv/) - customer lifetime value for the
  same check-to-virtual-card program: cohort retention heatmaps, survival
  curves, CLV four ways, per-channel conversion spend ceilings, and an RFM
  regression for next-month revenue.
- [`tpv_lstm_forecasting/`](tpv_lstm_forecasting/) - daily settled TPV
  forecasting for the virtual card program: an LSTM built by the book
  (windowing, chronological splits, loss diagnostics, 10-seed ensemble),
  honestly benchmarked to a tie against a linear baseline, with ablation
  and refit-cadence experiments.
