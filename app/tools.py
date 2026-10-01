"""
tools.py -- READ-ONLY tools (they never change the database). The agent will call these in Part B.

Most important rule: every tool takes customer_email and only shows an order if it belongs to that customer.
An order that belongs to someone else and an order that does not exist produce exactly the same answer.
"""
import os
from app.db import get_conn

NOT_FOUND = {"found": False, "reason": "order_not_found_on_account"}


def _norm(email: str | None) -> str:
    return (email or "").strip().lower()


def _owned_order_row(con, order_id, customer_email):
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return None
    row = con.execute(
        """SELECT o.*, c.email AS customer_email, c.name AS customer_name
           FROM orders o JOIN customers c ON c.customer_id = o.customer_id
           WHERE o.order_id = ?""", (order_id,)).fetchone()
    if row is None or _norm(row["customer_email"]) != _norm(customer_email):
        return None
    return row


def lookup_order(order_id, customer_email: str) -> dict:
    con = get_conn()
    try:
        row = _owned_order_row(con, order_id, customer_email)
    finally:
        con.close()
    if row is None:
        return dict(NOT_FOUND)
    return {
        "found": True,
        "order_id": row["order_id"],
        "item": row["item"],
        "quantity": row["quantity"],
        "amount": row["amount"],
        "status": row["status"],
        "order_date": row["order_date"],
        "shipped_date": row["shipped_date"],
        "delivered_date": row["delivered_date"],
        "shipping_address": row["shipping_address"],
        "refunded": bool(row["refunded"]),
    }


def find_orders_by_email(customer_email: str) -> dict:
    """Used when the ticket has no order number."""
    con = get_conn()
    try:
        rows = con.execute(
            """SELECT o.order_id, o.item, o.amount, o.status, o.order_date
               FROM orders o JOIN customers c ON c.customer_id = o.customer_id
               WHERE lower(c.email) = ? ORDER BY o.order_date DESC, o.order_id DESC""",
            (_norm(customer_email),)).fetchall()
    finally:
        con.close()
    orders = [dict(r) for r in rows]
    return {"found": bool(orders), "count": len(orders), "orders": orders}


def track_shipment(order_id, customer_email: str) -> dict:
    con = get_conn()
    try:
        row = _owned_order_row(con, order_id, customer_email)
        if row is None:
            return dict(NOT_FOUND)
        ship = con.execute("SELECT * FROM shipments WHERE order_id = ?", (row["order_id"],)).fetchone()
    finally:
        con.close()
    if ship is None:
        return {"found": True, "order_id": row["order_id"], "shipped": False, "status": "processing",
                "message": "Order has not shipped yet."}
    return {
        "found": True,
        "order_id": row["order_id"],
        "shipped": True,
        "status": ship["status"],            # in_transit / out_for_delivery / delivered
        "carrier": ship["carrier"],
        "tracking_number": ship["tracking_number"],
        "expected_date": ship["expected_date"],
        "delivered_date": row["delivered_date"],
    }


def get_policy() -> str:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "refund_policy.md")
    with open(path, encoding="utf-8") as f:
        return f.read()
