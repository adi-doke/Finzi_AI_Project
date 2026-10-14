from __future__ import annotations

import json
from calendar import monthrange
from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any

from ..models import BudgetGoal
from .finance_metrics import build_financial_snapshot, month_key, safe_float, normalize_category
from .ollama_client import ollama_client


ESSENTIAL_CATEGORIES = {
    "groceries",
    "food",
    "rent",
    "utilities",
    "transport",
    "healthcare",
}


def _current_month_transactions(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return snapshot.get("current_month_transactions", [])


def _monthly_income_average(snapshot: dict[str, Any]) -> float:
    values = [float(item["income"]) for item in snapshot.get("monthly_trends", []) if float(item.get("income", 0)) > 0]
    return round(mean(values), 2) if values else 0.0


def _category_spend(snapshot: dict[str, Any]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for tx in _current_month_transactions(snapshot):
        if tx.get("type") != "debit":
            continue
        totals[normalize_category(tx.get("category"))] += safe_float(tx.get("amount"))
    return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


def _suggest_category_budgets(snapshot: dict[str, Any]) -> dict[str, float]:
    category_spend = _category_spend(snapshot)
    suggested: dict[str, float] = {}
    for category, amount in category_spend.items():
        if category.lower() in ESSENTIAL_CATEGORIES:
            suggested[category] = round(amount * 1.05, 2)
        else:
            suggested[category] = round(amount * 0.9, 2)
    return suggested


def _suggest_savings_goal(snapshot: dict[str, Any]) -> float:
    avg_income = _monthly_income_average(snapshot)
    current_income = safe_float(snapshot.get("current_month", {}).get("income"))
    spend = safe_float(snapshot.get("current_month", {}).get("expenses"))
    income_base = current_income or avg_income
    if income_base <= 0:
        return 0.0
    surplus = max(income_base - spend, 0.0)
    return round(max(income_base * 0.1, surplus * 0.5), 2)


def _ai_recommendation(snapshot: dict[str, Any], suggested_goal: float, suggested_categories: dict[str, float]) -> str:
    fallback = _fallback_recommendation(snapshot, suggested_goal, suggested_categories)
    if not ollama_client.is_available(timeout_seconds=0.35):
        return fallback

    prompt = f"""
Create a personalized monthly budget recommendation in a calm, helpful tone.
Do not invent numbers. Use the provided analytics only.

User analytics:
- Monthly income average: INR {_monthly_income_average(snapshot):,.2f}
- Current month income: INR {snapshot.get('current_month', {}).get('income', 0):,.2f}
- Current month expenses: INR {snapshot.get('current_month', {}).get('expenses', 0):,.2f}
- Suggested savings goal: INR {suggested_goal:,.2f}
- Suggested category budgets: {json.dumps(suggested_categories, indent=2)}

Answer with 3-5 short bullet points and practical next steps.
""".strip()
    messages = [
        {"role": "system", "content": "You are FinZi, a personal finance planner. Only explain the supplied budget analytics. Never invent financial details."},
        {"role": "user", "content": prompt},
    ]

    try:
        result = ollama_client.chat(messages, stream=False, timeout_seconds=4, resolve_model=False)
        text = ((result.get("message") or {}).get("content") or "").strip()
        if text:
            return text
    except Exception:
        pass

    return fallback


def _fallback_recommendation(snapshot: dict[str, Any], suggested_goal: float, suggested_categories: dict[str, float]) -> str:
    current_month = snapshot.get("current_month", {})
    income = safe_float(current_month.get("income"))
    expenses = safe_float(current_month.get("expenses"))
    projected = safe_float(current_month.get("projected_expenses"))
    total_budget = sum(safe_float(value) for value in suggested_categories.values())
    top_categories = list(suggested_categories.keys())[:3]

    lines = [
        f"Keep your monthly savings target near INR {suggested_goal:,.0f} before adding flexible spends.",
        f"Current expenses are INR {expenses:,.0f}; projected month-end expenses are INR {projected:,.0f}.",
    ]
    if income:
        lines.append(f"Use INR {income:,.0f} as the income base and review the plan again after large credits or bills.")
    if total_budget:
        lines.append(f"Your active category budget totals INR {total_budget:,.0f}. Watch {', '.join(top_categories)} first.")
    return "\n".join(f"- {line}" for line in lines)


def get_budget_overview(db, user_phone: str, use_ai: bool = True) -> dict[str, Any]:
    snapshot = build_financial_snapshot(db, user_phone)
    period = month_key(datetime.utcnow())

    suggested_categories = _suggest_category_budgets(snapshot)
    suggested_savings = _suggest_savings_goal(snapshot)
    current_spend = _category_spend(snapshot)
    total_current_spend = sum(current_spend.values())

    active_category_budgets = suggested_categories
    active_savings_goal = suggested_savings
    monthly_income = _monthly_income_average(snapshot) or safe_float(snapshot.get("current_month", {}).get("income"))

    category_progress = []
    for category, budget in active_category_budgets.items():
        spent = current_spend.get(category, 0.0)
        budget_value = safe_float(budget)
        progress = spent / budget_value if budget_value > 0 else 0.0
        category_progress.append(
            {
                "category": category,
                "spent": round(spent, 2),
                "budget": round(budget_value, 2),
                "progress": round(progress, 3),
            }
        )
    category_progress.sort(key=lambda item: item["progress"], reverse=True)

    days_in_month = monthrange(datetime.utcnow().year, datetime.utcnow().month)[1]
    days_elapsed = datetime.utcnow().day
    projected_spend = safe_float(snapshot.get("current_month", {}).get("projected_expenses"))
    if projected_spend <= 0 and days_elapsed > 0:
        projected_spend = round(total_current_spend / days_elapsed * days_in_month, 2) if total_current_spend else 0.0

    total_active_budget = sum(safe_float(value) for value in active_category_budgets.values())
    remaining_budget = round(total_active_budget - total_current_spend, 2)
    warning = None
    if projected_spend > total_active_budget and active_category_budgets:
        warning = "At your current pace, you may exceed the category budget before month-end."

    ai_summary = (
        _ai_recommendation(snapshot, active_savings_goal, active_category_budgets)
        if use_ai
        else _fallback_recommendation(snapshot, active_savings_goal, active_category_budgets)
    )

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": period,
        "goal": {
            "monthly_income": monthly_income,
            "savings_goal": active_savings_goal,
            "category_budgets": active_category_budgets,
            "notes": None,
        },
        "suggested": {
            "monthly_income": monthly_income,
            "savings_goal": suggested_savings,
            "category_budgets": suggested_categories,
        },
        "tracking": {
            "current_spend": round(total_current_spend, 2),
            "remaining_budget": remaining_budget,
            "projected_spend": round(projected_spend, 2),
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
        },
        "category_progress": category_progress,
        "ai_recommendation": ai_summary,
        "warning": warning,
        "snapshot": {
            "summary": snapshot.get("summary", {}),
            "current_month": snapshot.get("current_month", {}),
            "top_categories": snapshot.get("top_categories", []),
            "recent_transactions": snapshot.get("recent_transactions", []),
        },
    }


def save_budget_goal(db, user_phone: str, payload: dict[str, Any]) -> BudgetGoal:
    period = (payload.get("period_key") or month_key(datetime.utcnow())).strip()
    monthly_income = safe_float(payload.get("monthly_income"))
    savings_goal = safe_float(payload.get("savings_goal"))
    category_budgets = {
        str(category).strip(): round(safe_float(amount), 2)
        for category, amount in (payload.get("category_budgets") or {}).items()
        if str(category).strip()
    }
    notes = (payload.get("notes") or "").strip()

    return BudgetGoal(
        user_phone=user_phone,
        period_key=period,
        monthly_income=monthly_income,
        savings_goal=savings_goal,
        category_budgets=category_budgets,
        notes=notes,
    )
