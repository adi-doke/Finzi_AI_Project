from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from calendar import monthrange
from statistics import mean
from typing import Any

from sqlalchemy import case, func

from ..config import settings
from ..models import FinanceSummary, Transaction, User


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def normalize_category(value: str | None) -> str:
    return (value or "Unknown").strip() or "Unknown"


def normalize_merchant(value: str | None) -> str:
    return (value or "Unknown").strip() or "Unknown"


def month_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m")


def month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def current_month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.utcnow()
    start = month_start(now)
    end = datetime(start.year, start.month, monthrange(start.year, start.month)[1], 23, 59, 59, 999999)
    return start, end


def get_month_column(column, db_session):
    dialect_name = db_session.bind.dialect.name
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m", column)
    return func.date_format(column, "%Y-%m")


def _fetch_transactions(db, user_phone: str, since: datetime) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_phone == user_phone)
        .filter(Transaction.ts >= since)
        .order_by(Transaction.ts.asc())
        .all()
    )


def _group_monthly_transactions(transactions: list[Transaction]) -> dict[str, dict[str, float]]:
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    for tx in transactions:
        bucket = monthly[month_key(tx.ts)]
        amount = safe_float(tx.amount)
        if (tx.txn_type or "").lower() == "credit":
            bucket["income"] += amount
        else:
            bucket["expenses"] += amount
    return monthly


def _detect_recurring_payments(transactions: list[Transaction]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, float], list[Transaction]] = defaultdict(list)
    for tx in transactions:
        if (tx.txn_type or "").lower() != "debit":
            continue
        signature = (
            normalize_merchant(tx.merchant).lower(),
            normalize_category(tx.category).lower(),
            round(safe_float(tx.amount), 2),
        )
        grouped[signature].append(tx)

    recurring = []
    for (merchant, category, amount), rows in grouped.items():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=lambda item: item.ts)
        deltas = [(rows[idx].ts - rows[idx - 1].ts).days for idx in range(1, len(rows))]
        average_gap = mean(deltas) if deltas else 0
        if len(rows) >= 3 or 20 <= average_gap <= 40:
            recurring.append(
                {
                    "merchant": merchant.title(),
                    "category": category.title(),
                    "average_amount": round(amount, 2),
                    "count": len(rows),
                    "average_gap_days": round(average_gap, 1) if deltas else None,
                    "estimated_monthly_cost": round(amount * len(rows), 2),
                }
            )

    recurring.sort(key=lambda item: (-item["count"], -item["estimated_monthly_cost"]))
    return recurring[:8]


def _detect_weekend_spending(transactions: list[Transaction]) -> dict[str, float]:
    weekend = 0.0
    weekday = 0.0
    for tx in transactions:
        if (tx.txn_type or "").lower() != "debit":
            continue
        if tx.ts.weekday() >= 5:
            weekend += safe_float(tx.amount)
        else:
            weekday += safe_float(tx.amount)
    total = weekend + weekday
    share = weekend / total if total else 0.0
    return {"weekend": round(weekend, 2), "weekday": round(weekday, 2), "weekend_share": round(share, 3)}


def _top_categories(transactions: list[Transaction], limit: int = 6) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for tx in transactions:
        if (tx.txn_type or "").lower() != "debit":
            continue
        totals[normalize_category(tx.category)] += safe_float(tx.amount)
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [{"category": name, "spent": round(amount, 2)} for name, amount in ranked[:limit]]


def _top_merchants(transactions: list[Transaction], limit: int = 6) -> list[dict[str, Any]]:
    totals: dict[str, float] = defaultdict(float)
    for tx in transactions:
        if (tx.txn_type or "").lower() != "debit":
            continue
        totals[normalize_merchant(tx.merchant)] += safe_float(tx.amount)
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [{"merchant": name, "spent": round(amount, 2)} for name, amount in ranked[:limit]]


def _build_current_month_breakdown(transactions: list[Transaction]) -> dict[str, Any]:
    start, end = current_month_bounds()
    current = [tx for tx in transactions if start <= tx.ts <= end]
    category_totals: dict[str, float] = defaultdict(float)
    income = 0.0
    expenses = 0.0
    for tx in current:
        amount = safe_float(tx.amount)
        if (tx.txn_type or "").lower() == "credit":
            income += amount
        else:
            expenses += amount
            category_totals[normalize_category(tx.category)] += amount

    days_elapsed = max(1, datetime.utcnow().day)
    days_in_month = monthrange(start.year, start.month)[1]
    projected = expenses / days_elapsed * days_in_month if expenses else 0.0
    top_categories = sorted(category_totals.items(), key=lambda item: item[1], reverse=True)

    return {
        "income": round(income, 2),
        "expenses": round(expenses, 2),
        "savings": round(income - expenses, 2),
        "projected_expenses": round(projected, 2),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "top_categories": [{"category": name, "spent": round(amount, 2)} for name, amount in top_categories[:6]],
    }


def build_financial_snapshot(db, user_phone: str, lookback_days: int = 3650) -> dict[str, Any]:
    user = db.get(User, user_phone)
    finance = db.query(FinanceSummary).filter(FinanceSummary.user_phone == user_phone).first()
    since = datetime.utcnow() - timedelta(days=lookback_days)
    transactions = _fetch_transactions(db, user_phone, since)
    current_start, current_end = current_month_bounds()
    current_month_transactions = [tx for tx in transactions if current_start <= tx.ts <= current_end]
    current_period = month_key(datetime.utcnow())
    monthly = _group_monthly_transactions(transactions)
    recurring = _detect_recurring_payments(transactions)
    weekend = _detect_weekend_spending(transactions)
    current_breakdown = _build_current_month_breakdown(transactions)

    month_keys = sorted(monthly.keys())
    monthly_trends = []
    for key in month_keys[-6:]:
        bucket = monthly[key]
        monthly_trends.append(
            {
                "month": key,
                "income": round(bucket["income"], 2),
                "expenses": round(bucket["expenses"], 2),
                "savings": round(bucket["income"] - bucket["expenses"], 2),
            }
        )

    monthly_income_values = [item["income"] for item in monthly_trends if item["income"] > 0]
    monthly_expense_values = [item["expenses"] for item in monthly_trends if item["expenses"] > 0]

    current_month = current_breakdown
    total_assets = safe_float(getattr(finance, "bank_balance", 0)) + safe_float(getattr(finance, "mutual_funds", 0)) + safe_float(getattr(finance, "stocks", 0))
    total_liabilities = safe_float(getattr(finance, "loan", 0))
    net_worth = total_assets - total_liabilities
    average_income = round(mean(monthly_income_values), 2) if monthly_income_values else 0.0
    average_expenses = round(mean(monthly_expense_values), 2) if monthly_expense_values else 0.0

    snapshot = {
        "user": {"phone": user.phone, "name": user.name} if user else {"phone": user_phone, "name": "FinZi User"},
        "profile": {
            "bank_balance": round(safe_float(getattr(finance, "bank_balance", 0)), 2),
            "mutual_funds": round(safe_float(getattr(finance, "mutual_funds", 0)), 2),
            "stocks": round(safe_float(getattr(finance, "stocks", 0)), 2),
            "loan": round(safe_float(getattr(finance, "loan", 0)), 2),
            "credit_score": int(getattr(finance, "credit_score", 0) or 0),
            "updated_at": getattr(finance, "updated_at", None).isoformat() if finance and getattr(finance, "updated_at", None) else None,
        },
        "summary": {
            "assets_total": round(total_assets, 2),
            "liabilities_total": round(total_liabilities, 2),
            "net_worth": round(net_worth, 2),
            "average_monthly_income": average_income,
            "average_monthly_expenses": average_expenses,
            "current_month_income": current_month["income"],
            "current_month_expenses": current_month["expenses"],
            "current_month_savings": current_month["savings"],
            "projected_current_month_expenses": current_month["projected_expenses"],
        },
        "current_month": current_month,
        "current_month_transactions": [
            {
                "id": tx.id,
                "date": tx.ts.strftime("%Y-%m-%d"),
                "description": tx.description,
                "category": normalize_category(tx.category),
                "merchant": normalize_merchant(tx.merchant),
                "amount": round(safe_float(tx.amount), 2),
                "type": (tx.txn_type or "").lower(),
            }
            for tx in current_month_transactions
        ],
        "monthly_trends": monthly_trends,
        "top_categories": _top_categories(transactions),
        "top_merchants": _top_merchants(transactions),
        "recurring_payments": recurring,
        "weekend_spending": weekend,
        "recent_transactions": [
            {
                "id": tx.id,
                "date": tx.ts.strftime("%Y-%m-%d"),
                "description": tx.description,
                "category": normalize_category(tx.category),
                "merchant": normalize_merchant(tx.merchant),
                "amount": round(safe_float(tx.amount), 2),
                "type": (tx.txn_type or "").lower(),
            }
            for tx in transactions[-settings.max_recent_transactions :]
        ],
    }
    return snapshot


def detect_anomalies(db, user_phone: str, transactions: list[Transaction] | None = None, limit: int = 8) -> list[dict[str, Any]]:
    from ..ml.anomaly_detector import TransactionAnomalyDetector

    txs = transactions
    if txs is None:
        txs = _fetch_transactions(db, user_phone, datetime.utcnow() - timedelta(days=3650))

    anomalies: list[dict[str, Any]] = []
    detector = TransactionAnomalyDetector()
    for tx in reversed(txs[-60:]):
        if (tx.txn_type or "").lower() != "debit":
            continue
        flagged = False
        try:
            flagged = detector.is_anomaly(safe_float(tx.amount), normalize_category(tx.category))
        except Exception:
            flagged = False
        if flagged or safe_float(tx.amount) > _category_threshold(txs, tx):
            anomalies.append(
                {
                    "id": tx.id,
                    "date": tx.ts.strftime("%Y-%m-%d"),
                    "merchant": normalize_merchant(tx.merchant),
                    "category": normalize_category(tx.category),
                    "amount": round(safe_float(tx.amount), 2),
                    "reason": "Unusually high spend for this category",
                }
            )
        if len(anomalies) >= limit:
            break
    return anomalies


def _category_threshold(transactions: list[Transaction], target: Transaction) -> float:
    values = [
        safe_float(tx.amount)
        for tx in transactions
        if (tx.txn_type or "").lower() == "debit" and normalize_category(tx.category).lower() == normalize_category(target.category).lower()
    ]
    if len(values) < 3:
        return safe_float(target.amount) * 1.8
    avg = mean(values)
    return max(avg * 2.0, max(values) * 1.25)
