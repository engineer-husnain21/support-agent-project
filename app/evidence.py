"""
evidence.py -- everything a reviewer needs to judge an AI-resolved ticket, built from the audit log and the database:
  - the facts mentioned in the reply, and where each one was found
  - what the AI did (tool calls) and what the policy decided, in plain words
  - the data as it is now (order, refund records)
"""
import json

from app import audit, grounding, results, tickets, tools
from app.db import get_conn

REFUND_WHY = {
    "within_policy": "Refund allowed: delivered within 30 days and not above $50.",
    "above_auto_limit": "Refund is within policy but above the $50 limit, so a human had to approve it.",
    "outside_30_day_window": "Refund refused: more than 30 days since delivery.",
    "not_delivered": "Refund refused: the order has not been delivered.",
    "already_refunded": "Refund refused: this order was already refunded.",
    "order_not_found_on_account": "Refused: the order is not on this customer's account.",
}
ADDRESS_WHY = {
    "not_shipped_yet": "Address change allowed: the order has not shipped yet.",
    "already_shipped": "Address change refused: the order has already shipped.",
    "already_delivered": "Address change refused: the order was already delivered.",
    "order_not_found_on_account": "Refused: the order is not on this customer's account.",
    "address_not_in_ticket": "Refused: the new address was not written in the customer's message.",
    "invalid_address": "Refused: the new address looks incomplete.",
}


def _decisions(tool_calls: list) -> list:
    out = []
    for d in tool_calls:
        name, args, r = d.get("name"), d.get("args") or {}, d.get("result") or {}
        oid = args.get("order_id")
        if name == "issue_refund":
            if r.get("executed"):
                out.append({"kind": "action", "ok": True, "title": f"Refund of ${r.get('amount'):,.2f} executed on order #{oid} (simulated)",
                            "why": REFUND_WHY.get(r.get("reason"), r.get("message"))})
            else:
                out.append({"kind": "decision", "ok": False, "title": f"No refund on order #{oid}",
                            "why": REFUND_WHY.get(r.get("reason"), r.get("message"))})
        elif name == "update_address":
            if r.get("executed"):
                out.append({"kind": "action", "ok": True, "title": f"Address of order #{oid} changed (simulated)",
                            "why": f"New address: {r.get('new_address')}. " + ADDRESS_WHY.get(r.get("reason"), "")})
            else:
                out.append({"kind": "decision", "ok": False, "title": f"Address of order #{oid} not changed",
                            "why": ADDRESS_WHY.get(r.get("reason"), r.get("message"))})
        elif name in ("lookup_order", "track_shipment"):
            if r.get("found") is False:
                out.append({"kind": "lookup", "ok": False, "title": f"Order #{oid}: not found on this customer's account",
                            "why": "Nothing about that order may be shown to this customer."})
            elif name == "track_shipment" and r.get("shipped"):
                out.append({"kind": "lookup", "ok": True, "title": f"Shipment of order #{oid}",
                            "why": f"{r.get('carrier')}, {str(r.get('status', '')).replace('_', ' ')}, tracking {r.get('tracking_number')}, expected {r.get('expected_date')}"})
            elif name == "track_shipment":
                out.append({"kind": "lookup", "ok": True, "title": f"Shipment of order #{oid}", "why": "Not shipped yet."})
            elif name == "lookup_order":
                out.append({"kind": "lookup", "ok": True, "title": f"Order #{oid} details",
                            "why": f"{r.get('item')}, ${r.get('amount'):,.2f}, status {r.get('status')}"})
    return out


def _order_now(order_ids: list, email: str) -> dict | None:
    """The order as it is in the database now. An order that is not the customer's is never shown."""
    if not order_ids:
        return None
    oid = order_ids[0]
    order = tools.lookup_order(oid, email)
    if not order.get("found"):
        return {"found": False, "order_id": oid}
    con = get_conn()
    try:
        has = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='refunds'").fetchone()
        refunds = [dict(r) for r in con.execute("SELECT amount, approved_by, created_at FROM refunds WHERE order_id = ?", (oid,)).fetchall()] if has else []
    finally:
        con.close()
    return {**order, "refund_records": refunds}


def build_evidence(ticket_id: int) -> dict | None:
    t = tickets.get_ticket(ticket_id)
    res = results.get_result(ticket_id)
    if not t or not res:
        return None
    trail = audit.get_trail(ticket_id)
    tool_calls = [e["detail"] for e in trail if e["step"] == "tool_call"]
    tool_results = [d["result"] for d in tool_calls if "result" in d]

    order_ids = []
    for e in trail:
        if e["step"] == "intent" and e["detail"].get("order_id"):
            order_ids.append(e["detail"]["order_id"])
    for d in tool_calls:
        oid = (d.get("args") or {}).get("order_id")
        if isinstance(oid, int) and oid not in order_ids:
            order_ids.append(oid)

    customer_text = f"Subject: {t['subject']}\n\n{t['body']}" + "".join(f"\nOrder #{i}" for i in order_ids[:1])
    facts = grounding.fact_table(res["reply"] or "", tool_results, customer_text)
    return {
        "facts": facts,
        "facts_ok": all(f["ok"] for f in facts),
        "decisions": _decisions(tool_calls),
        "order_now": _order_now(order_ids, t["customer_email"]),
        "tools_used": len(tool_calls),
        "llm_used": any(e["step"] == "intent" for e in trail),
    }
