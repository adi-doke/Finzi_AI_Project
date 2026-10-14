from __future__ import annotations

import textwrap
from datetime import datetime
from typing import Any

from .budget_service import get_budget_overview
from .finance_metrics import build_financial_snapshot, month_key, safe_float
from .insights_service import build_insights_payload


def _format_currency(value: Any) -> str:
    amount = safe_float(value)
    return f"INR {amount:,.2f}"


def build_monthly_report_payload(db, user_phone: str) -> dict[str, Any]:
    snapshot = build_financial_snapshot(db, user_phone)
    budget = get_budget_overview(db, user_phone, use_ai=False)
    insights = build_insights_payload(db, user_phone, use_ai=False)

    summary = snapshot.get("summary", {})
    current_month = snapshot.get("current_month", {})
    user = snapshot.get("user", {"phone": user_phone, "name": "FinZi User"})

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period": month_key(datetime.utcnow()),
        "user": user,
        "summary": {
            "income": summary.get("current_month_income", 0.0),
            "expenses": summary.get("current_month_expenses", 0.0),
            "savings": summary.get("current_month_savings", 0.0),
            "net_worth": summary.get("net_worth", 0.0),
            "projected_expenses": summary.get("projected_current_month_expenses", 0.0),
        },
        "budget": {
            "monthly_income": budget.get("goal", {}).get("monthly_income", 0.0),
            "savings_goal": budget.get("goal", {}).get("savings_goal", 0.0),
            "current_spend": budget.get("tracking", {}).get("current_spend", 0.0),
            "remaining_budget": budget.get("tracking", {}).get("remaining_budget", 0.0),
            "warning": budget.get("warning"),
        },
        "ai_summary": insights.get("summary", ""),
        "insights": insights.get("insights", []),
        "top_categories": snapshot.get("top_categories", [])[:5],
        "top_merchants": snapshot.get("top_merchants", [])[:5],
        "monthly_trends": snapshot.get("monthly_trends", []),
        "recent_transactions": snapshot.get("recent_transactions", [])[-10:],
        "current_month": current_month,
    }


def _wrap_lines(text: str, width: int = 92) -> list[str]:
    return textwrap.wrap(text, width=width) or [""]


def _line_items(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    lines.append("FINZI MONTHLY REPORT")
    lines.append(f"User: {report['user'].get('name', 'FinZi User')}  |  Period: {report['period']}")
    lines.append(f"Generated: {report['generated_at']}")
    lines.append("")

    summary = report.get("summary", {})
    lines.append("OVERVIEW")
    lines.append(f"Income: {_format_currency(summary.get('income', 0))}")
    lines.append(f"Expenses: {_format_currency(summary.get('expenses', 0))}")
    lines.append(f"Savings: {_format_currency(summary.get('savings', 0))}")
    lines.append(f"Net worth: {_format_currency(summary.get('net_worth', 0))}")
    lines.append(f"Projected expenses: {_format_currency(summary.get('projected_expenses', 0))}")
    lines.append("")

    budget = report.get("budget", {})
    lines.append("BUDGET")
    lines.append(f"Monthly income target: {_format_currency(budget.get('monthly_income', 0))}")
    lines.append(f"Savings goal: {_format_currency(budget.get('savings_goal', 0))}")
    lines.append(f"Current spend: {_format_currency(budget.get('current_spend', 0))}")
    lines.append(f"Remaining budget: {_format_currency(budget.get('remaining_budget', 0))}")
    if budget.get("warning"):
        lines.append(f"Warning: {budget['warning']}")
    lines.append("")

    lines.append("AI SUMMARY")
    lines.extend(_wrap_lines(report.get("ai_summary") or "No AI summary available."))
    lines.append("")

    lines.append("TOP CATEGORIES")
    for item in report.get("top_categories", []):
        lines.append(f"- {item.get('category', 'Unknown')}: {_format_currency(item.get('spent', 0))}")
    if not report.get("top_categories"):
        lines.append("- No category data available")
    lines.append("")

    lines.append("TOP MERCHANTS")
    for item in report.get("top_merchants", []):
        lines.append(f"- {item.get('merchant', 'Unknown')}: {_format_currency(item.get('spent', 0))}")
    if not report.get("top_merchants"):
        lines.append("- No merchant data available")
    lines.append("")

    lines.append("RECENT TRANSACTIONS")
    for tx in report.get("recent_transactions", []):
        lines.append(
            f"- {tx.get('date', '')} | {tx.get('merchant', 'Unknown')} | {tx.get('category', 'Unknown')} | {_format_currency(tx.get('amount', 0))}"
        )
    if not report.get("recent_transactions"):
        lines.append("- No recent transactions available")
    lines.append("")

    lines.append("KEY INSIGHTS")
    for item in report.get("insights", [])[:5]:
        lines.append(f"- {item.get('title', 'Insight')}: {item.get('detail', '')}")
    if not report.get("insights"):
        lines.append("- No insights available")

    return lines


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_monthly_report_pdf(report: dict[str, Any]) -> bytes:
    lines = _line_items(report)

    pages: list[list[str]] = []
    current_page: list[str] = []
    remaining = 44

    for line in lines:
        wrapped = _wrap_lines(line, width=92) if line else [""]
        for item in wrapped:
            if remaining <= 0:
                pages.append(current_page)
                current_page = []
                remaining = 44
            current_page.append(item)
            remaining -= 1
    if current_page:
        pages.append(current_page)

    if not pages:
        pages = [["FINZI MONTHLY REPORT", "No data available."]]

    objects: list[tuple[int, bytes]] = []
    objects.append((1, b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj"))

    kids = " ".join(f"{4 + index * 2} 0 R" for index in range(len(pages)))
    objects.append((2, f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {len(pages)} >> endobj".encode("ascii")))
    objects.append((3, b"3 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj"))

    for index, page in enumerate(pages):
        content_object_number = 5 + index * 2
        page_object_number = 4 + index * 2
        stream_lines = [
            "BT",
            "/F1 12 Tf",
            "50 790 Td",
            "14 TL",
        ]
        for line_index, line in enumerate(page):
            if line_index == 0:
                stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
            else:
                stream_lines.append("T*")
                stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
        stream_lines.append("ET")
        stream_text = "\n".join(stream_lines).encode("utf-8")
        content_obj = (
            f"{content_object_number} 0 obj << /Length {len(stream_text)} >> stream\n".encode("ascii")
            + stream_text
            + b"\nendstream\nendobj"
        )
        page_obj = (
            f"{page_object_number} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_object_number} 0 R >> endobj"
        ).encode("ascii")
        objects.append((page_object_number, page_obj))
        objects.append((content_object_number, content_obj))

    final = bytearray()
    final.extend(b"%PDF-1.4\n")

    offsets: dict[int, int] = {}
    for obj_number, obj_bytes in objects:
        offsets[obj_number] = len(final)
        final.extend(obj_bytes)
        final.extend(b"\n")

    xref_start = len(final)
    max_object_number = max(offsets)
    final.extend(f"xref\n0 {max_object_number + 1}\n".encode("ascii"))
    final.extend(b"0000000000 65535 f \n")
    for obj_number in range(1, max_object_number + 1):
        offset = offsets.get(obj_number, 0)
        final.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    final.extend(
        f"trailer << /Size {max_object_number + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode("ascii")
    )
    return bytes(final)
