"""
grounding.py -- the anti-hallucination check. NO AI, only regex and set comparison.

Every order number, dollar amount, date and tracking number in a reply must already exist in the
tool results (or in the customer's own message). If the reply mentions something the tools never
returned, the reply is blocked.
"""
import json
import re
from dataclasses import dataclass, field

ORDER_RE = re.compile(r"(?:order\s*(?:number|no\.?|id)?\s*#?\s*|#)(\d{3,6})", re.IGNORECASE)
AMOUNT_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
TRACKING_RE = re.compile(r"\bTRK\d+\b")

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
_MONTH = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
TEXT_DATE_1 = re.compile(rf"\b{_MONTH}\s+(\d{{1,2}})\b", re.IGNORECASE)                 # October 2
TEXT_DATE_2 = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MONTH}", re.IGNORECASE)    # 2nd October

# Amounts that are part of the written policy are always allowed in a reply.
POLICY_AMOUNTS = {50.0}


@dataclass
class GroundingResult:
    ok: bool
    problems: list = field(default_factory=list)


def _walk(obj):
    """Yield every (key, value) pair in nested dicts/lists."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _to_float(text: str) -> float:
    return float(text.replace(",", ""))


def check_reply(reply: str, tool_results: list, ticket_text: str = "") -> GroundingResult:
    blob = json.dumps(tool_results, default=str) + "\n" + (ticket_text or "")
    problems = []

    # --- order numbers
    allowed_numbers = {int(n) for n in re.findall(r"\b\d{3,6}\b", blob)}
    for n in ORDER_RE.findall(reply):
        if int(n) not in allowed_numbers:
            problems.append(f"order number {n} not found in tool results")

    # --- dollar amounts
    allowed_amounts = set(POLICY_AMOUNTS)
    allowed_amounts |= {_to_float(a) for a in AMOUNT_RE.findall(blob)}
    for key, value in _walk(tool_results):
        if key == "amount" and isinstance(value, (int, float)):
            allowed_amounts.add(float(value))
    for a in AMOUNT_RE.findall(reply):
        if round(_to_float(a), 2) not in {round(x, 2) for x in allowed_amounts}:
            problems.append(f"amount ${a} not found in tool results")

    # --- dates
    iso_in_blob = set(ISO_DATE_RE.findall(blob))
    allowed_md = {(int(m), int(d)) for _, m, d in iso_in_blob}
    for y, m, d in ISO_DATE_RE.findall(reply):
        if (y, m, d) not in iso_in_blob:
            problems.append(f"date {y}-{m}-{d} not found in tool results")
    for mon, day in TEXT_DATE_1.findall(reply):
        if (MONTHS[mon.lower()[:3]], int(day)) not in allowed_md:
            problems.append(f"date '{mon} {day}' not found in tool results")
    for day, mon in TEXT_DATE_2.findall(reply):
        if (MONTHS[mon.lower()[:3]], int(day)) not in allowed_md:
            problems.append(f"date '{day} {mon}' not found in tool results")

    # --- tracking numbers
    for trk in TRACKING_RE.findall(reply):
        if trk not in blob:
            problems.append(f"tracking number {trk} not found in tool results")

    return GroundingResult(ok=not problems, problems=problems)


def fact_table(reply: str, tool_results: list, ticket_text: str = "") -> list:
    """Every order number, amount, date and tracking number in the reply, and where it was found.
    Used by the review screen. 'where' is None when the fact was found nowhere (that would be a wrong fact)."""
    tool_blob = json.dumps(tool_results, default=str)
    cust = ticket_text or ""
    rows = []

    def add(kind, value, where):
        if not any(r["kind"] == kind and r["value"] == value for r in rows):
            rows.append({"kind": kind, "value": value, "where": where, "ok": where is not None})

    tool_numbers = {int(n) for n in re.findall(r"\b\d{3,6}\b", tool_blob)}
    cust_numbers = {int(n) for n in re.findall(r"\b\d{3,6}\b", cust)}
    for n in ORDER_RE.findall(reply or ""):
        n = int(n)
        add("Order number", f"#{n}", "system data" if n in tool_numbers else "customer message" if n in cust_numbers else None)

    tool_amounts = {round(_to_float(a), 2) for a in AMOUNT_RE.findall(tool_blob)}
    for key, value in _walk(tool_results):
        if key == "amount" and isinstance(value, (int, float)):
            tool_amounts.add(round(float(value), 2))
    cust_amounts = {round(_to_float(a), 2) for a in AMOUNT_RE.findall(cust)}
    for a in AMOUNT_RE.findall(reply or ""):
        v = round(_to_float(a), 2)
        where = ("system data" if v in tool_amounts else "policy limit" if v in {round(x, 2) for x in POLICY_AMOUNTS}
                 else "customer message" if v in cust_amounts else None)
        add("Amount", f"${v:,.2f}", where)

    tool_iso = set(ISO_DATE_RE.findall(tool_blob))
    cust_iso = set(ISO_DATE_RE.findall(cust))
    tool_md = {(int(m), int(d)) for _, m, d in tool_iso}
    for y, m, d in ISO_DATE_RE.findall(reply or ""):
        add("Date", f"{y}-{m}-{d}", "system data" if (y, m, d) in tool_iso else "customer message" if (y, m, d) in cust_iso else None)
    for mon, day in TEXT_DATE_1.findall(reply or ""):
        add("Date", f"{mon} {day}", "system data" if (MONTHS[mon.lower()[:3]], int(day)) in tool_md else None)
    for day, mon in TEXT_DATE_2.findall(reply or ""):
        add("Date", f"{day} {mon}", "system data" if (MONTHS[mon.lower()[:3]], int(day)) in tool_md else None)

    for trk in TRACKING_RE.findall(reply or ""):
        add("Tracking number", trk, "system data" if trk in tool_blob else None)
    return rows
