from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class LoanScenario:
    """Fixed-rate loan scenario with optional extra principal payments."""

    name: str
    principal: float
    annual_rate: float
    term_months: int
    start_date: date
    extra_payments: dict[date, float] = field(default_factory=dict)


def add_months(value: date, months: int) -> date:
    """Move a date forward by whole months while preserving month-end safety."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def monthly_payment(principal: float, annual_rate: float, months: int) -> float:
    """Calculate the fixed monthly payment for a fully amortizing loan."""
    if principal <= 0:
        raise ValueError("principal must be positive")
    if months <= 0:
        raise ValueError("months must be positive")

    monthly_rate = annual_rate / 12
    if monthly_rate == 0:
        return round(principal / months, 2)

    factor = (1 + monthly_rate) ** months
    payment = principal * monthly_rate * factor / (factor - 1)
    return round(payment, 2)


def build_schedule(scenario: LoanScenario) -> list[dict[str, Any]]:
    """Build a monthly amortization schedule.

    Assumptions:
    - Interest accrues monthly on the opening balance.
    - The scheduled payment is applied first.
    - Any extra principal payment is applied after the scheduled payment.
    - Extra payments are capped at the remaining principal balance.
    """
    payment = monthly_payment(scenario.principal, scenario.annual_rate, scenario.term_months)
    monthly_rate = scenario.annual_rate / 12
    balance = scenario.principal
    total_interest = 0.0
    rows: list[dict[str, Any]] = []

    for month_number in range(1, scenario.term_months + 1):
        payment_date = add_months(scenario.start_date, month_number - 1)
        interest = round(balance * monthly_rate, 2)
        scheduled_principal = min(round(payment - interest, 2), balance)

        if scheduled_principal <= 0:
            raise ValueError("payment does not cover accrued interest")

        remaining_after_payment = round(balance - scheduled_principal, 2)
        requested_extra = round(scenario.extra_payments.get(payment_date, 0.0), 2)
        extra_principal = min(requested_extra, remaining_after_payment)

        balance = round(remaining_after_payment - extra_principal, 2)
        total_interest = round(total_interest + interest, 2)
        actual_payment = round(interest + scheduled_principal + extra_principal, 2)

        rows.append(
            {
                "payment_number": month_number,
                "date": payment_date,
                "scheduled_payment": min(payment, round(interest + scheduled_principal, 2)),
                "interest": interest,
                "scheduled_principal": scheduled_principal,
                "extra_principal": extra_principal,
                "actual_payment": actual_payment,
                "ending_balance": max(balance, 0.0),
                "total_interest": total_interest,
            }
        )

        if balance <= 0:
            break

    return rows


def summarize(scenario: LoanScenario) -> dict[str, Any]:
    schedule = build_schedule(scenario)
    total_interest = schedule[-1]["total_interest"]
    return {
        "scenario": scenario.name,
        "monthly_payment": monthly_payment(
            scenario.principal,
            scenario.annual_rate,
            scenario.term_months,
        ),
        "months_to_payoff": len(schedule),
        "payoff_date": schedule[-1]["date"],
        "total_interest": total_interest,
        "total_extra_principal": round(sum(row["extra_principal"] for row in schedule), 2),
        "total_paid": round(scenario.principal + total_interest, 2),
    }


def compare_scenarios(baseline: LoanScenario, alternative: LoanScenario) -> dict[str, Any]:
    base = summarize(baseline)
    alt = summarize(alternative)
    months_saved = base["months_to_payoff"] - alt["months_to_payoff"]
    interest_saved = round(base["total_interest"] - alt["total_interest"], 2)
    total_extra = alt["total_extra_principal"] - base["total_extra_principal"]

    return {
        "months_saved": months_saved,
        "years_saved": round(months_saved / 12, 2),
        "interest_saved": interest_saved,
        "total_extra_principal": total_extra,
        "interest_saved_per_extra_dollar": round(interest_saved / total_extra, 2)
        if total_extra
        else None,
        "baseline_payoff_date": base["payoff_date"],
        "alternative_payoff_date": alt["payoff_date"],
    }


def default_scenarios() -> tuple[LoanScenario, LoanScenario]:
    principal = 359_200.00
    annual_rate = 0.0625
    term_months = 30 * 12
    start_date = date(2023, 11, 1)

    baseline = LoanScenario(
        name="Baseline",
        principal=principal,
        annual_rate=annual_rate,
        term_months=term_months,
        start_date=start_date,
    )

    accelerated = LoanScenario(
        name="Accelerated payoff",
        principal=principal,
        annual_rate=annual_rate,
        term_months=term_months,
        start_date=start_date,
        extra_payments={
            date(2023, 11, 1): 4_000.00,
            date(2023, 12, 1): 4_000.00,
            date(2024, 1, 1): 5_000.00,
        },
    )

    return baseline, accelerated


def currency(value: float) -> str:
    return f"${value:,.2f}"


def print_summary(scenarios: list[LoanScenario]) -> None:
    header = (
        f"{'Scenario':<20} {'Payment':>12} {'Months':>8} {'Payoff':>12} "
        f"{'Interest':>15} {'Total paid':>15} {'Extra':>12}"
    )
    print(header)
    print("-" * len(header))
    for scenario in scenarios:
        row = summarize(scenario)
        print(
            f"{row['scenario']:<20} "
            f"{currency(row['monthly_payment']):>12} "
            f"{row['months_to_payoff']:>8} "
            f"{row['payoff_date'].isoformat():>12} "
            f"{currency(row['total_interest']):>15} "
            f"{currency(row['total_paid']):>15} "
            f"{currency(row['total_extra_principal']):>12}"
        )


def main() -> None:
    baseline, accelerated = default_scenarios()
    print_summary([baseline, accelerated])
    impact = compare_scenarios(baseline, accelerated)
    print()
    print(f"Months saved: {impact['months_saved']}")
    print(f"Interest saved: {currency(impact['interest_saved'])}")
    print(
        "Interest saved per extra principal dollar: "
        f"${impact['interest_saved_per_extra_dollar']:.2f}"
    )


if __name__ == "__main__":
    main()
