from __future__ import annotations

from .services.ollama_client import ollama_client
from .services.chat_service import generate_reply, stream_reply


def get_financial_answer(user_query: str, user_context: dict | None = None) -> str:
    user_context = user_context or {}
    recent_transactions = user_context.get("recent_transactions") or []
    context_lines = [
        f"Bank balance: INR {float(user_context.get('bank_balance', 0) or 0):,.2f}",
        f"Mutual funds: INR {float(user_context.get('mutual_funds', 0) or 0):,.2f}",
        f"Stocks: INR {float(user_context.get('stocks', 0) or 0):,.2f}",
        f"Loan: INR {float(user_context.get('loan', 0) or 0):,.2f}",
        f"Credit score: {int(user_context.get('credit_score', 0) or 0)}",
        f"Net worth: INR {float(user_context.get('net_worth', 0) or 0):,.2f}",
    ]
    if recent_transactions:
        context_lines.append("Recent transactions:")
        for tx in recent_transactions[:10]:
            context_lines.append(
                f"- {tx.get('date')} | {tx.get('description')} | {tx.get('category')} | INR {float(tx.get('amount', 0) or 0):,.2f} | {tx.get('type')}"
            )

    messages = [
        {
            "role": "system",
            "content": "You are FinZi, a helpful personal finance assistant. Only answer using the provided financial context. Do not invent numbers or mention other users.",
        },
        {"role": "user", "content": "\n".join(context_lines) + f"\n\nUser question: {user_query}"},
    ]
    try:
        result = ollama_client.chat(messages, stream=False)
        reply = ((result.get("message") or {}).get("content") or "").strip()
        if reply:
            return reply
    except Exception:
        pass

    return "The local AI model is temporarily unavailable."


def generate_financial_reply(db, user_phone: str, user_query: str, history: list[dict] | None = None) -> dict:
    return generate_reply(db, user_phone, user_query, history)


def stream_financial_reply(db, user_phone: str, user_query: str, history: list[dict] | None = None):
    return stream_reply(db, user_phone, user_query, history)
