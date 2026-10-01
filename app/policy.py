"""
policy.py -- ALL business rules live here, in plain Python. The AI has no say in them.

Each function returns a Decision:
  allowed     -> go ahead
  needs_human -> within the rules, but a human must approve it
  denied      -> not possible (the reason says why)
"""
from dataclasses import dataclass, asdict
from datetime import date

REFUND_WINDOW_DAYS = 30        # within 30 days of delivery
AUTO_REFUND_LIMIT_CENTS = 5000  # refunds up to $50.00 are automatic (in cents, to avoid float issues)


@dataclass(frozen=True)
class Decision:
    decision: str   # allowed / needs_human / denied
    reason: str     # short code, e.g. "outside_30_day_window"
    message: str    # one line for a human reader

    def to_dict(self) -> dict:
        return asdict(self)


def _denied(reason: str, message: str) -> Decision:
    return Decision("denied", reason, message)


def check_refund(order: dict | None, today: date) -> Decision:
    """order: the result of tools.lookup_order() (ownership has already been checked)."""
    if not order or not order.get("found"):
        return _denied("order_not_found_on_account", "Order not found on this account.")
    if order["status"] != "delivered":
        return _denied("not_delivered", "Only delivered orders can be refunded.")
    if order.get("refunded"):
        return _denied("already_refunded", "This order has already been refunded.")

    days = (today - date.fromisoformat(order["delivered_date"])).days
    if days > REFUND_WINDOW_DAYS:
        return _denied("outside_30_day_window",
                       f"Delivered {days} days ago; refunds are only available within {REFUND_WINDOW_DAYS} days.")

    if round(order["amount"] * 100) > AUTO_REFUND_LIMIT_CENTS:
        return Decision("needs_human", "above_auto_limit",
                        f"Refund of ${order['amount']:.2f} is within policy but above the $50 auto-approval limit.")

    return Decision("allowed", "within_policy", "Refund is within policy and under the auto-approval limit.")


def check_address_change(order: dict | None) -> Decision:
    if not order or not order.get("found"):
        return _denied("order_not_found_on_account", "Order not found on this account.")
    status = order["status"]
    if status == "processing":
        return Decision("allowed", "not_shipped_yet", "Order has not shipped; address can be changed.")
    if status == "shipped":
        return _denied("already_shipped", "Order has already shipped; the address can no longer be changed.")
    if status == "delivered":
        return _denied("already_delivered", "Order was already delivered.")
    return _denied("unknown_status", f"Cannot change address for status '{status}'.")
