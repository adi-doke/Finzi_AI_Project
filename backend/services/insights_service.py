from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from .finance_metrics import build_financial_snapshot, detect_anomalies, month_key
from .ollama_client import ollama_client


def _percent_change(current: float, previous: float) -> float | None:
    if previous <= 0:
        return None
    return ((current - previous) / previous) * 100.0


def _build_rule_insights(snapshot: dict[str, Any], anomalies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    monthly = snapshot.get("monthly_trends", [])
    current_month = snapshot.get("current_month", {})
    budget_goal = snapshot.get("budget_goal") or {}
    recurring = snapshot.get("recurring_payments", [])
    weekend = snapshot.get("weekend_spending", {})

    if len(monthly) >= 2:
        latest = monthly[-1]
        previous = monthly[-2]
        category_latest = {item["category"]: item["spent"] for item in snapshot.get("top_categories", [])}
        if category_latest:
            top_category = max(category_latest.items(), key=lambda item: item[1])
            insights.append(
                {
                    "type": "trend",
                    "title": f"{top_category[0]} is your biggest spend area",
                    "detail": f"You spent INR {top_category[1]:,.0f} on {top_category[0].lower()} in the current window.",
                    "severity": "info",
                }
            )
        income_change = _percent_change(latest["income"], previous["income"])
        expense_change = _percent_change(latest["expenses"], previous["expenses"])
        savings_change = _percent_change(latest["savings"], previous["savings"])
        if expense_change is not None and expense_change > 15:
            insights.append(
                {
                    "type": "warning",
                    "title": "Spending is trending upward",
                    "detail": f"Your expenses are up {expense_change:.0f}% versus the previous month.",
                    "severity": "warning",
                }
            )
        if savings_change is not None and savings_change > 0:
            insights.append(
                {
                    "type": "positive",
                    "title": "You are saving more",
                    "detail": f"Your savings improved by {savings_change:.0f}% compared with the previous month.",
                    "severity": "success",
                }
            )

    projected = current_month.get("projected_expenses", 0.0)
    if budget_goal.get("savings_goal", 0):
        target = float(budget_goal.get("savings_goal", 0))
        if current_month.get("expenses", 0.0) > 0 and projected > target + current_month.get("income", 0.0):
            insights.append(
                {
                    "type": "risk",
                    "title": "You may miss this month’s savings target",
                    "detail": f"Projected spending is INR {projected:,.0f}, which could pressure your savings goal of INR {target:,.0f}.",
                    "severity": "warning",
                }
            )
    elif projected > current_month.get("income", 0.0) and current_month.get("income", 0.0) > 0:
        insights.append(
            {
                "type": "risk",
                "title": "Projected spending is above income",
                "detail": f"At the current pace, projected expenses are INR {projected:,.0f} against income of INR {current_month.get('income', 0.0):,.0f}.",
                "severity": "warning",
            }
        )

    if recurring:
        recurring_total = sum(float(item.get("estimated_monthly_cost", 0)) for item in recurring[:5])
        insights.append(
            {
                "type": "subscription",
                "title": "Recurring payments detected",
                "detail": f"We found {len(recurring)} recurring payments worth about INR {recurring_total:,.0f} monthly.",
                "severity": "info",
            }
        )

    weekend_share = weekend.get("weekend_share", 0.0)
    if weekend_share >= 0.35 and weekend.get("weekend", 0.0) > weekend.get("weekday", 0.0):
        insights.append(
            {
                "type": "behavior",
                "title": "Weekend spending is unusually high",
                "detail": f"Weekend purchases account for {weekend_share:.0%} of debit spend in the current period.",
                "severity": "warning",
            }
        )

    if anomalies:
        top = anomalies[0]
        insights.append(
            {
                "type": "anomaly",
                "title": "Potential overspend detected",
                "detail": f"{top['merchant']} on {top['date']} was unusually high at INR {top['amount']:,.0f}.",
                "severity": "warning",
            }
        )

    if not insights:
        insights.append(
            {
                "type": "neutral",
                "title": "No major anomalies detected",
                "detail": "Your current spending pattern looks stable based on the available data.",
                "severity": "info",
            }
        )

    return insights[:8]


def _fallback_summary(insights: list[dict[str, Any]]) -> str:
    fallback_lines = [f"- {item['title']}: {item['detail']}" for item in insights[:4]]
    return " ".join(fallback_lines) if fallback_lines else "Your current spending pattern looks stable based on the available data."


def _build_ai_summary(snapshot: dict[str, Any], insights: list[dict[str, Any]], use_ai: bool = True) -> str:
    metrics = snapshot.get("summary", {})
    fallback_summary = _fallback_summary(insights)
    if not use_ai:
        return fallback_summary

    prompt = f"""
Summarize these finance insights for the user in a friendly, natural voice.
Do not invent numbers. Keep it to 3-5 short sentences.

Key metrics:
- Net worth: INR {metrics.get('net_worth', 0):,.2f}
- Current month income: INR {metrics.get('current_month_income', 0):,.2f}
- Current month expenses: INR {metrics.get('current_month_expenses', 0):,.2f}
- Current month savings: INR {metrics.get('current_month_savings', 0):,.2f}
- Projected month expenses: INR {metrics.get('projected_current_month_expenses', 0):,.2f}

Rule-based insights:
{insights}
""".strip()

    messages = [
        {
            "role": "system",
            "content": "You are FinZi, a personal finance coach. Only summarize the provided data. Be concise and practical.",
        },
{"role": "user", "content": prompt},
    ]

    try:
        if not ollama_client.is_available(timeout_seconds=0.35):
            return fallback_summary
        result = ollama_client.chat(messages, stream=False, timeout_seconds=3, resolve_model=False)
        text = ((result.get("message") or {}).get("content") or "").strip()
        if text:
            return text
    except Exception:
        pass

    return fallback_summary


def build_insights_payload(db, user_phone: str, use_ai: bool = True) -> dict[str, Any]:
    snapshot = build_financial_snapshot(db, user_phone)
    anomalies = detect_anomalies(db, user_phone)
    insights = _build_rule_insights(snapshot, anomalies)
    ai_summary = _build_ai_summary(snapshot, insights, use_ai=use_ai)
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": month_key(datetime.utcnow()),
        "summary": ai_summary,
        "insights": insights,
        "snapshot": {
            "summary": snapshot.get("summary", {}),
            "top_categories": snapshot.get("top_categories", []),
            "top_merchants": snapshot.get("top_merchants", []),
            "monthly_trends": snapshot.get("monthly_trends", []),
            "recurring_payments": snapshot.get("recurring_payments", []),
            "weekend_spending": snapshot.get("weekend_spending", {}),
        },
    }
