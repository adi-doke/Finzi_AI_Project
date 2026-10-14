from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from .auth import require_api_user
from .database import SessionLocal
from .services.budget_service import get_budget_overview, save_budget_goal


budget_bp = Blueprint("budget", __name__, url_prefix="/api/budget")


@budget_bp.route("/plan", methods=["GET"])
@require_api_user
def get_plan():
    db = SessionLocal()
    try:
        return jsonify(get_budget_overview(db, g.current_user_phone))
    finally:
        db.close()


@budget_bp.route("/plan", methods=["POST"])
@require_api_user
def upsert_plan():
    payload = request.get_json(force=True, silent=True) or {}
    db = SessionLocal()
    try:
        goal = save_budget_goal(db, g.current_user_phone, payload)
        return jsonify(
            {
                "success": True,
                "goal": {
                    "period_key": goal.period_key,
                    "monthly_income": goal.monthly_income,
                    "savings_goal": goal.savings_goal,
                    "category_budgets": goal.category_budgets,
                    "notes": goal.notes,
                },
            }
        )
    finally:
        db.close()
