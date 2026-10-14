from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from .auth import require_api_user, require_user_page
from .database import SessionLocal
from .services.receipt_service import analyze_receipt


receipts_bp = Blueprint("receipts", __name__)


@receipts_bp.route("/receipt-upload")
@require_user_page
def receipt_upload_page():
    return render_template("index.html")


@receipts_bp.route("/api/receipts/analyze", methods=["POST"])
@require_api_user
def analyze_receipt_route():
    payload = request.get_json(force=True, silent=True) or {}
    raw_text = (payload.get("raw_text") or "").strip()
    filename = (payload.get("filename") or "").strip() or None
    if not raw_text:
        return jsonify({"success": False, "message": "Receipt text is required"}), 400

    return jsonify({"success": True, "receipt": analyze_receipt(raw_text, filename)})
