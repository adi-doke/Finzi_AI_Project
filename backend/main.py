from __future__ import annotations

from datetime import datetime, timedelta

from flask import Flask, Response, jsonify, redirect, render_template, request, send_from_directory, stream_with_context
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

from .auth import (
    current_user_name,
    current_user_phone,
    login_user,
    logout_user,
    require_api_user,
    require_user_page,
)
from .config import settings
from .database import SessionLocal, init_db
from .insights import insights_bp
from .models import BudgetGoal, ChatSession, FinanceSummary, Transaction, User
from .ai_service import generate_financial_reply, stream_financial_reply


BASE_DIR = __import__("os").path.dirname(__file__)
TEMPLATES_DIR = __import__("os").path.join(BASE_DIR, "..", "frontend")
REACT_DIST_DIR = __import__("os").path.join(TEMPLATES_DIR, "dist")
STATIC_DIR = __import__("os").path.join(TEMPLATES_DIR, "static")


app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    template_folder=REACT_DIST_DIR if __import__("os").path.exists(REACT_DIST_DIR) else TEMPLATES_DIR,
)
app.secret_key = settings.secret_key
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=settings.session_days),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=settings.session_cookie_secure,
)
CORS(app, supports_credentials=True)

init_db()
app.register_blueprint(insights_bp)


@app.route("/assets/<path:filename>")
def react_assets(filename: str):
    return send_from_directory(__import__("os").path.join(REACT_DIST_DIR, "assets"), filename)


def db():
    return SessionLocal()


def _finance_payload(fs: FinanceSummary | None) -> dict:
    if not fs:
        return {
            "bank_balance": 0.0,
            "mutual_funds": 0.0,
            "stocks": 0.0,
            "loan": 0.0,
            "credit_score": 0,
        }
    return {
        "bank_balance": float(fs.bank_balance or 0),
        "mutual_funds": float(fs.mutual_funds or 0),
        "stocks": float(fs.stocks or 0),
        "loan": float(fs.loan or 0),
        "credit_score": int(fs.credit_score or 0),
    }


def _require_matching_phone(phone: str) -> bool:
    logged_in = current_user_phone()
    return bool(logged_in and phone and phone.strip() == logged_in)


def _normalize_phone(value: str) -> str:
    digits = "".join(char for char in (value or "") if char.isdigit())
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    return digits


def _lockout_remaining_seconds(user: User) -> int:
    if not user.lockout_until:
        return 0
    remaining = int((user.lockout_until - datetime.utcnow()).total_seconds())
    return max(remaining, 0)


def _register_failed_login(user: User) -> None:
    user.failed_login_attempts = int(user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= 5:
        user.lockout_until = datetime.utcnow() + timedelta(minutes=10)


def _clear_failed_login(user: User) -> None:
    user.failed_login_attempts = 0
    user.lockout_until = None


@app.route("/")
def index():
    if current_user_phone():
        return render_template("index.html")
    return redirect("/login")


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("index.html")


@app.route("/register", methods=["GET"])
@app.route("/signup", methods=["GET"])
def register_page():
    if current_user_phone():
        return render_template("index.html")
    return render_template("index.html")


@app.route("/landing", methods=["GET"])
def landing_page():
    return render_template("index.html")


@app.route("/chat_page")
@require_user_page
def chat_page():
    return render_template("index.html")


@app.route("/insights")
@require_user_page
def insights_page():
    return render_template("index.html")


@app.route("/portfolio")
@require_user_page
def portfolio_page():
    return render_template("index.html")


@app.route("/budget")
@require_user_page
def budget_page():
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    phone = _normalize_phone(data.get("phone") or "")
    password = data.get("password") or ""
    if not phone or not password:
        return jsonify({"success": False, "message": "Missing phone or password"}), 400

    session = db()
    try:
        user = session.get(User, phone)
        if user and _lockout_remaining_seconds(user):
            remaining = _lockout_remaining_seconds(user)
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Account temporarily locked. Try again in {max(1, remaining // 60)} minute(s).",
                        "lockout_remaining_seconds": remaining,
                    }
                ),
                423,
            )

        if not user or not check_password_hash(user.password, password):
            if user:
                _register_failed_login(user)
                session.commit()
            return jsonify({"success": False, "message": "Invalid credentials"}), 401

        _clear_failed_login(user)
        session.commit()
        login_user(user)
        finance = session.query(FinanceSummary).filter_by(user_phone=phone).first()
        return jsonify(
            {
                "success": True,
                "user": {"name": user.name, "phone": user.phone, "email": getattr(user, "email", None)},
                "finance": _finance_payload(finance),
                "redirect": request.args.get("next") or "/",
            }
        )
    finally:
        session.close()


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = _normalize_phone(data.get("phone") or "")
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not name or not phone or not password:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    session = db()
    try:
        if session.get(User, phone):
            return jsonify({"success": False, "message": "Phone already registered"}), 409

        user = User(phone=phone, name=name, email=email or None, password=generate_password_hash(password))
        session.add(user)
        session.add(FinanceSummary(user_phone=phone))
        session.commit()
        return jsonify({"success": True, "message": "Registered successfully"})
    finally:
        session.close()


@app.route("/api/auth/me")
def auth_me():
    phone = current_user_phone()
    if not phone:
        return jsonify({"authenticated": False}), 200

    session = db()
    try:
        user = session.get(User, phone)
        return jsonify(
            {
                "authenticated": True,
                "user": {
                    "name": user.name if user else current_user_name(),
                    "phone": user.phone if user else phone,
                    "email": user.email if user else None,
                },
            }
        )
    finally:
        session.close()


@app.route("/api/profile", methods=["GET"])
@require_api_user
def api_profile():
    from flask import g

    session = db()
    try:
        user = session.get(User, g.current_user_phone)
        finance = session.query(FinanceSummary).filter_by(user_phone=g.current_user_phone).first()
        return jsonify(
            {
                "user": {
                    "name": user.name if user else current_user_name(),
                    "phone": user.phone if user else g.current_user_phone,
                    "email": user.email if user else None,
                },
                "finance": _finance_payload(finance),
            }
        )
    finally:
        session.close()


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    phone = current_user_phone()
    if phone:
        session = db()
        try:
            chat_sessions = session.query(ChatSession).filter(ChatSession.user_phone == phone).all()
            for chat_session in chat_sessions:
                session.delete(chat_session)
            session.query(BudgetGoal).filter(BudgetGoal.user_phone == phone).delete(synchronize_session=False)
            session.commit()
        finally:
            session.close()
    logout_user()
    return jsonify({"success": True})


@app.route("/api/account/delete", methods=["POST"])
@require_api_user
def account_delete():
    from flask import g

    session = db()
    try:
        user = session.get(User, g.current_user_phone)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        session.delete(user)
        session.commit()
        logout_user()
        return jsonify({"success": True, "message": "Account deleted"})
    finally:
        session.close()


@app.route("/api/me/finance", methods=["GET"])
@require_api_user
def me_finance():
    from flask import g

    session = db()
    try:
        finance = session.query(FinanceSummary).filter_by(user_phone=g.current_user_phone).first()
        user = session.get(User, g.current_user_phone)
        return jsonify(
            {
                "user": {"name": user.name if user else current_user_name()},
                "finance": _finance_payload(finance),
            }
        )
    finally:
        session.close()


@app.route("/mcp/<phone>", methods=["GET"])
@require_api_user
def get_mcp(phone):
    from flask import g

    if not _require_matching_phone(phone):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    session = db()
    try:
        finance = session.query(FinanceSummary).filter_by(user_phone=g.current_user_phone).first()
        return jsonify(_finance_payload(finance))
    finally:
        session.close()


@app.route("/api/transactions", methods=["GET"])
@require_api_user
def get_transactions():
    from flask import g

    limit = min(int(request.args.get("limit") or 100), 500)
    offset = max(int(request.args.get("offset") or 0), 0)
    session = db()
    try:
        rows = (
            session.query(Transaction)
            .filter(Transaction.user_phone == g.current_user_phone)
            .order_by(Transaction.ts.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        out = [
            {
                "id": row.id,
                "amount": row.amount,
                "currency": row.currency,
                "category": row.category,
                "merchant": row.merchant,
                "txn_type": row.txn_type,
                "description": row.description,
                "ts": row.ts.isoformat(),
            }
            for row in rows
        ]
        return jsonify(out)
    finally:
        session.close()


@app.route("/api/chat", methods=["POST"])
@app.route("/query", methods=["POST"])
@require_api_user
def chat():
    from flask import g
    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "Message is required"}), 400

    history = data.get("history")
    if not isinstance(history, list):
        history = []
    session = db()
    try:
        result = generate_financial_reply(session, g.current_user_phone, message, history)
        return jsonify(result)
    finally:
        session.close()


@app.route("/api/chat/stream", methods=["POST"])
@require_api_user
def chat_stream():
    from flask import g

    data = request.get_json(force=True, silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "message": "Message is required"}), 400

    history = data.get("history")
    if not isinstance(history, list):
        history = []

    def generate():
        session = db()
        try:
            yield from stream_financial_reply(session, g.current_user_phone, message, history)
        finally:
            session.close()

    return Response(stream_with_context(generate()), mimetype="text/plain; charset=utf-8")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "ollama_host": settings.ollama_host, "ollama_model": settings.ollama_chat_model})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
