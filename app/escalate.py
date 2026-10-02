"""
escalate.py -- builds what the human queue shows: a reason, a short summary and (when it makes sense)
a suggested reply. All of it is built by the code from facts, with no LLM involved.
"""
from app import tickets

REASON_TEXT = {
    "spam": "Looks like spam from an unknown sender.",
    "prompt_injection": "The message tries to override the rules or give system instructions.",
    "legal_threat": "The customer made a legal threat.",
    "angry_customer": "The customer is angry.",
    "unclear_request": "The request is too unclear for the agent.",
    "above_auto_limit": "The refund is within policy but above the $50 auto-approval limit, so a human must approve it.",
    "system_unavailable": "A system or tool failed while handling this ticket.",
    "unsupported_request": "The request is not something the agent can handle.",
    "no_orders_found": "No orders were found for this sender.",
    "ungrounded_reply": "The agent's reply contained facts that were not found in the order data, so it was blocked.",
    "step_limit_reached": "The agent used all its steps without finishing.",
    "agent_escalated": "The agent asked for a human.",
}


def _first_name(email: str) -> str:
    name = tickets.get_customer_name(email)
    return name.split()[0] if name else "there"


REQUEST_TEXT = {"refund": "a refund", "track": "order tracking", "address_change": "an address change", "other": "something else"}
STEP_TEXT = {"lookup_order": "looked up the order", "track_shipment": "checked the shipment",
             "issue_refund": "checked the refund policy", "update_address": "checked the address policy",
             "escalate_to_human": "asked for a human"}


def build_summary(ticket: dict, reason: str, intents=None, order_id=None, tools_used=None, detail=None) -> str:
    """One paragraph for the human agent, built from facts (no LLM)."""
    who = tickets.get_customer_name(ticket["customer_email"]) or ticket["customer_email"]
    if intents:
        wants = " and ".join(REQUEST_TEXT.get(i, i) for i in intents)
        parts = [f"{who} is asking for {wants}" + (f" about order #{order_id}." if order_id else ".")]
    else:
        body = " ".join((ticket["body"] or "").split())
        parts = [f"{who} wrote: \"{body[:110]}{'...' if len(body) > 110 else ''}\""]
    parts.append(f"Why a human is needed: {REASON_TEXT.get(reason, reason)}")
    if detail:
        parts.append(f"Detail: {detail}.")
    if tools_used:
        steps = list(dict.fromkeys(STEP_TEXT.get(t, t) for t in tools_used))
        parts.append(f"The agent already {' and '.join(steps)}.")
    return " ".join(parts)


def suggested_reply(reason: str, ticket: dict, pending_action: dict | None = None) -> str | None:
    first = _first_name(ticket["customer_email"])
    if reason == "above_auto_limit" and pending_action and pending_action.get("type") == "refund":
        return (f"Hi {first}, your refund of ${pending_action['amount']:.2f} for order #{pending_action['order_id']} "
                f"({pending_action.get('item', 'your item')}) has been approved. It will go back to your original "
                f"payment method within 5-7 business days.\n\nSupport Team")
    if reason == "angry_customer":
        return (f"Hi {first}, I'm very sorry about the trouble. I have passed your message to a senior team member "
                f"who will contact you personally as soon as possible.\n\nSupport Team")
    if reason == "unclear_request":
        return (f"Hi {first}, thanks for reaching out. Could you tell us your order number and what you need help "
                f"with?\n\nSupport Team")
    return None   # spam, injection, legal, system errors: a human writes these from scratch
