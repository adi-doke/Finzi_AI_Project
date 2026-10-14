from __future__ import annotations

from flask import Blueprint, Response, jsonify, render_template

from .auth import require_api_user, require_user_page
from .database import SessionLocal
from .services.report_service import build_monthly_report_payload, build_monthly_report_pdf


reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/monthly-report")
@require_user_page
def monthly_report_page():
    return render_template("index.html")


@reports_bp.route("/api/reports/monthly", methods=["GET"])
@require_api_user
def monthly_report_json():
    from flask import g

    db = SessionLocal()
    try:
        return jsonify(build_monthly_report_payload(db, g.current_user_phone))
    finally:
        db.close()


@reports_bp.route("/api/reports/monthly.pdf", methods=["GET"])
@require_api_user
def monthly_report_pdf():
    from flask import g

    db = SessionLocal()
    try:
        report = build_monthly_report_payload(db, g.current_user_phone)
        pdf_bytes = build_monthly_report_pdf(report)
        filename = f"finzi-monthly-report-{report['period']}.pdf"
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        db.close()
