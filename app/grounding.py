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
