from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from .auth import require_api_user
from .database import SessionLocal
from .models import Transaction
from .services.finance_metrics import get_month_column
from .services.insights_service import build_insights_payload


insights_bp = Blueprint("insights", __name__, url_prefix="/api/insights")


def _db():
    return SessionLocal()


def _recent_month_keys(db=None, user_phone: str | None = None, count: int = 12) -> list[str]:
    if db is not None and user_phone:
        rows = (
            db.query(Transaction.ts)
            .filter(Transaction.user_phone == user_phone)
            .order_by(Transaction.ts.asc())
            .all()
        )
        if rows:
            start = min(row[0] for row in rows).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = max(row[0] for row in rows).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            months: list[str] = []
            current = start
            while current <= end:
                months.append(current.strftime("%Y-%m"))
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)
            return months[-count:]

    current = datetime.utcnow().replace(day=1)
    months = []
    for offset in range(count - 1, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            month += 12
            year -= 1
        months.append(f"{year:04d}-{month:02d}")
    return months


@insights_bp.route("/monthly_spending", methods=["GET"])
@require_api_user
def monthly_spending():
    from flask import g

    db = _db()
    try:
        month_fmt = get_month_column(Transaction.ts, db)
        rows = (
            db.query(
                month_fmt.label("month"),
                Transaction.txn_type,
                Transaction.amount,
            )
            .filter(Transaction.user_phone == g.current_user_phone)
            .all()
        )
        monthly = {}
        for row in rows:
            bucket = monthly.setdefault(row.month, 0.0)
            if (row.txn_type or "").lower() == "debit":
                monthly[row.month] = bucket + float(row.amount or 0)
        months = _recent_month_keys(db, g.current_user_phone)
        amounts = [round(monthly.get(m, 0.0), 2) for m in months]
        return jsonify({"months": months, "amounts": amounts})
    finally:
        db.close()


@insights_bp.route("/category_spending", methods=["GET"])
@require_api_user
def category_spending():
    from flask import g
    from sqlalchemy import case, desc, func

    db = _db()
    try:
        days = int(request.args.get("days") or 3650)
        rows = (
            db.query(
                Transaction.category.label("category"),
                func.sum(case((Transaction.txn_type == "debit", Transaction.amount), else_=0)).label("spent"),
            )
            .filter(Transaction.user_phone == g.current_user_phone)
            .filter(Transaction.ts >= datetime.utcnow() - timedelta(days=days))
            .group_by(Transaction.category)
            .order_by(desc("spent"))
            .limit(20)
            .all()
        )
        return jsonify(
            {
                "categories": [row.category or "Unknown" for row in rows],
                "amounts": [round(float(row.spent or 0), 2) for row in rows],
            }
        )
    finally:
        db.close()


@insights_bp.route("/income_vs_expenses", methods=["GET"])
@require_api_user
def income_vs_expenses():
    from flask import g
    from sqlalchemy import case, func

    db = _db()
    try:
        month_fmt = get_month_column(Transaction.ts, db)
        rows = (
            db.query(
                month_fmt.label("month"),
                func.sum(case((Transaction.txn_type == "credit", Transaction.amount), else_=0)).label("income"),
                func.sum(case((Transaction.txn_type == "debit", Transaction.amount), else_=0)).label("expenses"),
            )
            .filter(Transaction.user_phone == g.current_user_phone)
            .filter(Transaction.ts >= datetime.utcnow() - timedelta(days=180))
            .group_by("month")
            .order_by("month")
            .all()
        )
        months = _recent_month_keys(db, g.current_user_phone)
        income_map = {row.month: float(row.income or 0) for row in rows}
        expense_map = {row.month: float(row.expenses or 0) for row in rows}
        return jsonify(
            {
                "months": months,
                "income": [round(income_map.get(m, 0.0), 2) for m in months],
                "expenses": [round(expense_map.get(m, 0.0), 2) for m in months],
            }
        )
    finally:
        db.close()


@insights_bp.route("/top_merchants", methods=["GET"])
@require_api_user
def top_merchants():
    from flask import g
    from sqlalchemy import case, desc, func

    db = _db()
    try:
        days = int(request.args.get("days") or 3650)
        limit = int(request.args.get("limit") or 10)
        rows = (
            db.query(
                Transaction.merchant.label("merchant"),
                func.sum(case((Transaction.txn_type == "debit", Transaction.amount), else_=0)).label("spent"),
            )
            .filter(Transaction.user_phone == g.current_user_phone)
            .filter(Transaction.ts >= datetime.utcnow() - timedelta(days=days))
            .group_by(Transaction.merchant)
            .order_by(desc("spent"))
            .limit(limit)
            .all()
        )
        return jsonify(
            {
                "merchants": [row.merchant or "Unknown" for row in rows],
                "amounts": [round(float(row.spent or 0), 2) for row in rows],
            }
        )
    finally:
        db.close()


@insights_bp.route("/net_worth_trend", methods=["GET"])
@require_api_user
def net_worth_trend():
    from flask import g
    from .models import FinanceSummary

    db = _db()
    try:
        finance = db.query(FinanceSummary).filter_by(user_phone=g.current_user_phone).first()
        months = _recent_month_keys(db, g.current_user_phone)
        if finance:
            net_worth = (
                float(finance.bank_balance or 0)
                + float(finance.mutual_funds or 0)
                + float(finance.stocks or 0)
                - float(finance.loan or 0)
            )
        else:
            net_worth = 0.0
        return jsonify({"months": months, "net_worth": [round(net_worth, 2) for _ in months]})
    finally:
        db.close()


@insights_bp.route("/ai", methods=["GET"])
@require_api_user
def ai_insights():
    from flask import g

    db = _db()
    try:
        return jsonify(build_insights_payload(db, g.current_user_phone, use_ai=False))
    finally:
        db.close()
