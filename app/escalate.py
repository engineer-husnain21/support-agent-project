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


def build_summary(ticket: dict, reason: str, intents=None, order_id=None, tools_used=None, detail=None) -> str:
    body = " ".join((ticket["body"] or "").split())
    parts = [f"{ticket['customer_email']} wrote: \"{body[:160]}{'...' if len(body) > 160 else ''}\"."]
    parts.append(f"Why a human is needed: {REASON_TEXT.get(reason, reason)}")
    if detail:
        parts.append(f"Detail: {detail}")
    if intents:
        parts.append(f"Detected request: {', '.join(intents)}.")
    if order_id:
        parts.append(f"Order: #{order_id}.")
    if tools_used:
        parts.append(f"Agent steps so far: {', '.join(tools_used)}.")
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
