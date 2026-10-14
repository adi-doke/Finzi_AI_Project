from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import unquote


_AMOUNT_PATTERNS = [
    re.compile(r"(?:INR|Rs\.?|Rs)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.IGNORECASE),
    re.compile(r"(?:total|amount|grand total|payable|balance due)\D{0,20}([0-9][0-9,]*(?:\.[0-9]{1,2})?)", re.IGNORECASE),
]

_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
    re.compile(r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"),
    re.compile(r"\b([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4})\b"),
]

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "food": ("restaurant", "cafe", "dine", "food", "pizza", "burger", "delivery", "swiggy", "zomato"),
    "groceries": ("grocery", "supermarket", "mart", "market", "grocer", "fresh"),
    "transport": ("uber", "ola", "taxi", "metro", "bus", "cab", "fuel", "petrol", "diesel"),
    "shopping": ("amazon", "flipkart", "mall", "shop", "store", "fashion", "retail"),
    "utilities": ("electricity", "water", "gas", "internet", "broadband", "mobile", "recharge"),
    "healthcare": ("pharmacy", "hospital", "clinic", "medical", "medicine", "drug"),
    "entertainment": ("movie", "cinema", "netflix", "spotify", "game", "entertainment"),
    "rent": ("rent", "apartment", "lease", "housing"),
    "travel": ("hotel", "flight", "airlines", "booking", "travel", "trip"),
}

_NOISE_LINES = {
    "invoice",
    "receipt",
    "bill",
    "tax invoice",
    "gst",
    "thank you",
    "order id",
    "order no",
    "date",
    "time",
    "subtotal",
    "total",
    "grand total",
}


def _normalize_text(value: str | None) -> str:
    return (value or "").replace("\r", "\n").replace("\t", " ").strip()


def _candidate_lines(raw_text: str) -> list[str]:
    lines = []
    for line in raw_text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _try_parse_date(candidate: str) -> str | None:
    cleaned = candidate.replace(",", " ").strip()
    formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d/%m/%y",
        "%d-%m-%y",
        "%Y/%m/%d",
        "%Y-%m-%d",
        "%b %d %Y",
        "%B %d %Y",
        "%b %d %y",
        "%B %d %y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_amount(raw_text: str, lines: list[str]) -> float | None:
    for line in lines:
        for pattern in _AMOUNT_PATTERNS:
            match = pattern.search(line)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue

    amount_candidates = []
    for match in re.finditer(r"\b([0-9][0-9,]*(?:\.[0-9]{1,2})?)\b", raw_text):
        try:
            amount_candidates.append(float(match.group(1).replace(",", "")))
        except ValueError:
            continue
    if amount_candidates:
        return max(amount_candidates)
    return None


def _parse_date(raw_text: str, lines: list[str]) -> str | None:
    for line in lines:
        for pattern in _DATE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            parsed = _try_parse_date(match.group(1))
            if parsed:
                return parsed

    for match in re.finditer(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b", raw_text):
        parsed = _try_parse_date(match.group(1))
        if parsed:
            return parsed
    return None


def _parse_merchant(lines: list[str], filename: str | None = None) -> str:
    if filename:
        fallback = unquote(filename).rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_", " ").strip()
    else:
        fallback = ""

    for line in lines[:8]:
        lowered = line.lower()
        if any(noise in lowered for noise in _NOISE_LINES):
            continue
        if re.search(r"\b(INR|Rs\.?|Rs)\b", line, re.IGNORECASE):
            continue
        if re.search(r"\d", line):
            continue
        if len(line) >= 3:
            return line[:80]

    return fallback[:80] if fallback else "Unknown merchant"


def _infer_category(raw_text: str, merchant: str) -> str:
    haystack = f"{raw_text}\n{merchant}".lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category
    return "unknown"


def analyze_receipt(raw_text: str, filename: str | None = None) -> dict[str, Any]:
    text = _normalize_text(raw_text)
    lines = _candidate_lines(text)
    amount = _parse_amount(text, lines)
    merchant = _parse_merchant(lines, filename)
    receipt_date = _parse_date(text, lines)
    category = _infer_category(text, merchant)

    return {
        "merchant": merchant,
        "amount": round(amount, 2) if amount is not None else None,
        "date": receipt_date,
        "category": category,
        "currency": "INR",
        "raw_text": text,
        "source_name": filename,
    }
