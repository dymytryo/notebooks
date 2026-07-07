# Loan Amortization Payoff Scenario

A cleaned, portfolio-ready version of the original `Loan_Calculator.ipynb`.
The project models a fixed-rate amortizing loan and compares a baseline
payment schedule against a configurable early-principal payoff strategy.

## Why

Loan payoff discussions often focus on the payment amount, but the more useful
question is: *what changes when extra principal is applied early?* This notebook
answers that with a reproducible amortization schedule, total interest, payoff
date, and side-by-side scenario comparison.

## What the Notebook Does

1. **Defines a deterministic amortization engine** - fixed monthly payment,
   monthly interest accrual, scheduled principal, optional extra principal, and
   running balance.
2. **Builds two scenarios** - the original 30-year loan schedule and an
   accelerated payoff case with a recurring extra-principal plan.
3. **Quantifies the impact** - payoff date, months saved, interest avoided,
   total cash paid, and interest saved per extra principal dollar.
4. **Supports flexible extra payments** - choose the extra monthly amount,
   the number of months to repeat it, and the payment month where it starts.
5. **Keeps the model transparent** - the notebook and helper script use only
   the Python standard library.

## Headline Result

For the sample `$359,200` loan at `6.25%` over 30 years, applying `$4,000` of
extra principal per month for the first `3` payments:

- pays the loan off `32` months early;
- reduces total interest by `$59,001.15`;
- avoids about `$4.92` of interest for every extra principal dollar applied.

This is a scenario model for analysis and education, not financial advice.

## Files

- [`loan_amortization.ipynb`](loan_amortization.ipynb) - the cleaned notebook.
- [`loan_amortization.py`](loan_amortization.py) - reusable standard-library
  amortization functions.

## Run It

```sh
python loan_amortization.py
jupyter notebook loan_amortization.ipynb
```
