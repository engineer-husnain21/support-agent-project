"""
policy.py -- SAARE rules yahan hain, plain Python mein. AI ka isme koi dakhal nahi.

Har function ek Decision wapas karta hai:
  allowed     -> kar do
  needs_human -> rules ke andar hai, lekin insaan ki manzoori chahiye
  denied      -> nahi ho sakta (wajah reason mein)
"""
from dataclasses import dataclass, asdict
from datetime import date

REFUND_WINDOW_DAYS = 30        # delivery se 30 din tak
AUTO_REFUND_LIMIT_CENTS = 5000  # $50.00 tak auto (cents mein, taake float ka masla na ho)


@dataclass(frozen=True)
class Decision:
    decision: str   # allowed / needs_human / denied
    reason: str     # chhota code, jaise "outside_30_day_window"
    message: str    # insaan ke liye ek line

    def to_dict(self) -> dict:
        return asdict(self)


def _denied(reason: str, message: str) -> Decision:
    return Decision("denied", reason, message)


def check_refund(order: dict | None, today: date) -> Decision:
    """order: tools.lookup_order() ka result (ownership pehle hi check ho chuki hoti hai)."""
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
