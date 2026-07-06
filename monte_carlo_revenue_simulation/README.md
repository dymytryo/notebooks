# Monte Carlo Revenue Simulation

Estimating how much monthly payment volume an outreach campaign would yield
from converted merchant leads — as a distribution, not a point estimate.

## Why

Before committing call-team capacity to a campaign, we wanted to know the
realistic range of revenue outcomes, not just a single average. The simulation
answers: *given N leads and an assumed conversion rate, what does the
distribution of converted monthly volume look like?*

## What the Notebook Does

1. **Scenario sweep over historical conversion rates** — runs 10,000
   simulations each at 3% / 6% / 9% conversion across the full lead pool and
   reports mean, spread, and min/max with histograms.
2. **Campaign-sized scenarios** — simulates specific lead-count × conversion
   combinations (e.g. 10K leads at 20%, 50K at 10%) and summarizes them in a
   comparison table.

Each trial bootstrap-resamples the lead pool and applies a Bernoulli
conversion draw per lead, so both amount mix and conversion luck vary run to
run.

## Files

- [`monte_carlo_revenue_simulation.ipynb`](monte_carlo_revenue_simulation.ipynb) — the analysis.
- [`data/opportunity_per_cluster_sample.csv`](data/opportunity_per_cluster_sample.csv) —
  **synthetic** sample data (the original warehouse extract is not public).
- [`data/generate_sample_data.py`](data/generate_sample_data.py) — script that
  produced the sample, for full transparency on its shape.

## Run It

```sh
pip install pandas numpy matplotlib jupyter
jupyter notebook monte_carlo_revenue_simulation.ipynb
```

Runs end-to-end against the bundled sample; a fixed seed keeps published
outputs reproducible.
