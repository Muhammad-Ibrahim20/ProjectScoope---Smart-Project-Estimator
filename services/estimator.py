"""Estimation engine: every total (hours, weeks, cost) is calculated here in Python.

AI-provided totals are never trusted; only validated per-task hours are used.
"""
import math

DURATION_CAVEAT = (
    "Duration assumes the whole team works in parallel at the stated weekly hours. "
    "Task dependencies, team experience, reviews and project complexity can make "
    "real-world duration longer."
)
BUDGET_NOTE = (
    "All figures are approximate estimates. Costs cover development effort only; "
    "hosting, API subscriptions and other infrastructure costs are excluded. "
    "No currency conversion is applied."
)


def total_hours(tasks):
    """Sum the hours of validated tasks (the same tasks shown on screen)."""
    return round(sum(float(t["hours"]) for t in tasks), 2)


def duration_weeks(hours, weekly_hours, team_size):
    """Return (exact_weeks, display_weeks). Raises ValueError on invalid capacity."""
    if weekly_hours <= 0 or team_size <= 0:
        raise ValueError("Weekly hours and team size must be greater than zero.")
    exact = hours / (weekly_hours * team_size)
    display = math.ceil(round(exact, 6)) if exact > 0 else 0
    return round(exact, 2), display


def budget(hours, hourly_rate, contingency_percent):
    """Return (base_cost, contingency_amount, total_budget)."""
    if hourly_rate < 0:
        raise ValueError("Hourly rate cannot be negative.")
    if not 0 <= contingency_percent <= 100:
        raise ValueError("Contingency percent is out of range.")
    base = hours * hourly_rate
    contingency = base * contingency_percent / 100
    return round(base, 2), round(contingency, 2), round(base + contingency, 2)


def calculate(tasks, params):
    """Build the full estimation summary from tasks and validated request params."""
    hours = total_hours(tasks)
    exact, display = duration_weeks(hours, params["weekly_hours"], params["team_size"])
    base, contingency, total = budget(
        hours, params["hourly_rate"], params["contingency_percent"]
    )
    return {
        "total_hours": hours,
        "duration_weeks_exact": exact,
        "duration_weeks": display,
        "team_size": params["team_size"],
        "weekly_hours": params["weekly_hours"],
        "hourly_rate": params["hourly_rate"],
        "currency": params["currency"],
        "contingency_percent": params["contingency_percent"],
        "base_cost": base,
        "contingency_amount": contingency,
        "total_budget": total,
        "duration_caveat": DURATION_CAVEAT,
        "budget_note": BUDGET_NOTE,
        "approximate": True,
    }
