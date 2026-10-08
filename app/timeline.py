"""
timeline.py -- turns raw audit-log rows into the friendly step timeline shown in the UI,
e.g. "Looked up order #1042 -> Checked policy -> Refunded $24.99 (simulated)".

Each item: {"kind": ok|warn|stop|info, "title": str, "detail": str|None, "time": "HH:MM:SS", "step": raw step name}
"""
from app.escalate import REASON_TEXT


def _money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$?"


def _reason(code: str | None) -> str:
    return REASON_TEXT.get(code or "", (code or "").replace("_", " "))


def _tool_item(d: dict) -> tuple[str, str, str | None]:
    name, args, result = d.get("name"), d.get("args") or {}, d.get("result") or {}
    oid = args.get("order_id")
    if "error" in d:
        return "stop", f"Tool failed: {name}", "The tool raised an error, so nothing was guessed."
    if name == "lookup_order":
        if result.get("found"):
            return "info", f"Looked up order #{oid}", f"{result.get('item')} - {_money(result.get('amount'))} - {result.get('status')}"
        return "warn", f"Looked up order #{oid}: not found on this account", "No details were revealed."
    if name == "track_shipment":
        if result.get("found") is False:
            return "warn", f"Tracked order #{oid}: not found on this account", "No details were revealed."
        if not result.get("shipped"):
            return "info", f"Checked shipment for order #{oid}", "Not shipped yet."
        return "info", f"Tracked shipment for order #{oid}", f"{result.get('carrier')} - {result.get('status')} - expected {result.get('expected_date')}"
    if name == "issue_refund":
        if result.get("executed"):
            by = result.get("approved_by")
            return "ok", f"Checked policy -> Refunded {_money(result.get('amount'))} (simulated)", f"Approved by: {by}"
        if result.get("decision") == "needs_human":
            return "warn", "Checked policy -> refund needs human approval", result.get("message")
        return "stop", f"Checked policy -> refund refused: {(result.get('reason') or '').replace('_', ' ')}", result.get("message")
    if name == "update_address":
        if result.get("executed"):
            return "ok", f"Checked policy -> changed address of order #{oid}", f"New address: {result.get('new_address')}"
        return "stop", f"Checked policy -> address change refused: {(result.get('reason') or '').replace('_', ' ')}", result.get("message")
    if name == "escalate_to_human":
        return "warn", "Agent asked for a human", args.get("reason")
    return "info", f"Tool: {name}", None


def build_timeline(trail: list[dict]) -> list[dict]:
    items = []
    for e in trail:
        step, d = e["step"], e["detail"] or {}
        kind, title, detail = "info", step.replace("_", " ").capitalize(), None

        if step == "ticket_received":
            title = "Ticket received"
        elif step == "screen":
            if d.get("action") == "pass":
                kind, title = "ok", "Screened: nothing risky found"
            else:
                kind, title, detail = "stop", f"Screened: {d.get('reason', '').replace('_', ' ')} (priority {d.get('priority')})", d.get("message")
        elif step == "intent":
            if d.get("ok"):
                order = f" - order #{d['order_id']}" if d.get("order_id") else ""
                title, detail = "Understood the request", f"{', '.join(d.get('intents', []))}{order}"
            else:
                kind, title, detail = "stop", "Could not classify the request", d.get("error")
        elif step == "order_lookup_by_email":
            title, detail = "No order number: looked up the customer's orders", f"{d.get('count')} found"
        elif step == "tool_call":
            kind, title, detail = _tool_item(d)
        elif step == "grounding":
            if d.get("ok"):
                kind, title = "ok", "Grounding check passed" + (" (after one rewrite)" if d.get("retry") else "")
                detail = "Every order number, amount and date in the reply comes from a tool result."
            else:
                kind, title = "warn", "Grounding check blocked the reply"
                detail = "; ".join(d.get("problems", [])) + (" - rewriting once." if not d.get("retry") else "")
        elif step == "promise_check":
            kind, title = "warn", "Reply blocked: it promised a human follow-up"
            detail = "; ".join(d.get("matches", [])) + (" - rewriting once." if not d.get("retry") else "")
        elif step == "reply_sent_simulated":
            kind, title = "ok", "Reply sent (simulated)"
        elif step == "escalated":
            kind = "warn"
            title = f"Sent to the human queue: {d.get('reason', '').replace('_', ' ')}"
            detail = _reason(d.get("reason"))
        elif step == "agent_error":
            kind, title, detail = "stop", "The agent stopped because of an error", d.get("error")
        elif step == "human_review":
            v = d.get("verdict")
            kind = {"correct": "ok", "incorrect": "stop", "unsure": "warn"}.get(v, "info")
            title = f"Reviewed by {d.get('by')}: marked {v}"
            detail = d.get("reason_text") or d.get("note")
        elif step == "human_refund":
            if d.get("executed"):
                kind, title, detail = "ok", f"Human-approved refund executed: {_money(d.get('amount'))} (simulated)", f"Approved by: {d.get('approved_by')}"
            else:
                kind, title, detail = "stop", "Human-approved refund was blocked", d.get("message")
        elif step == "human_approved":
            kind, title = "ok", f"Approved by {d.get('by')}" + (" (reply edited)" if d.get("edited") else "")
        elif step == "human_rejected":
            kind, title = "stop", f"Rejected by {d.get('by')}"

        items.append({"kind": kind, "title": title, "detail": detail, "time": (e["created_at"] or "")[11:19], "step": step})
    return items
