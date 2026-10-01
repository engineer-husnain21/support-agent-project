"""
actions.py -- wo kaam jo database BADALTE hain (simulated refund, address change).

Sab se zaroori: har action ke ANDAR policy dobara check hoti hai. Yaani agar agent (ya koi bug)
galti se galat call kare, tab bhi code refuse kar dega.
  - refund ka amount parameter hi nahi hai: amount hamesha database se aata hai
  - 'approved_by_human' sirf human queue ka code lagayega, agent ke tool list mein ye hoga hi nahi
  - insaan ki manzoori sirf $50 limit ko override karti hai; 30 din ya already refunded jaise rules nahi
"""
from datetime import datetime
from app import policy, tools
from app.db import get_conn, store_today


def _ensure_tables(con):
    con.execute("""CREATE TABLE IF NOT EXISTS refunds (
        refund_id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, amount REAL,
        approved_by TEXT, simulated INTEGER DEFAULT 1, created_at TEXT)""")


def issue_refund(order_id, customer_email: str, approved_by_human: bool = False,
                 approved_by: str | None = None) -> dict:
    order = tools.lookup_order(order_id, customer_email)
    decision = policy.check_refund(order, store_today())

    if decision.decision == "denied" or (decision.decision == "needs_human" and not approved_by_human):
        return {"executed": False, **decision.to_dict()}

    who = (approved_by or "human") if approved_by_human else "auto"
    con = get_conn()
    try:
        _ensure_tables(con)
        con.execute("INSERT INTO refunds (order_id, amount, approved_by, simulated, created_at) VALUES (?,?,?,?,?)",
                    (order["order_id"], order["amount"], who, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        con.execute("UPDATE orders SET refunded = 1 WHERE order_id = ?", (order["order_id"],))
        con.commit()
    finally:
        con.close()
    return {"executed": True, "simulated": True, "order_id": order["order_id"], "amount": order["amount"],
            "approved_by": who, "decision": decision.decision, "reason": decision.reason,
            "message": f"Refund of ${order['amount']:.2f} issued (simulated)."}


def update_address(order_id, customer_email: str, new_address: str) -> dict:
    order = tools.lookup_order(order_id, customer_email)
    decision = policy.check_address_change(order)
    if decision.decision != "allowed":
        return {"executed": False, **decision.to_dict()}

    new_address = (new_address or "").strip()
    if len(new_address) < 8:
        return {"executed": False, "decision": "denied", "reason": "invalid_address",
                "message": "The new address looks incomplete."}

    con = get_conn()
    try:
        con.execute("UPDATE orders SET shipping_address = ? WHERE order_id = ?", (new_address, order["order_id"]))
        con.commit()
    finally:
        con.close()
    return {"executed": True, "order_id": order["order_id"], "old_address": order["shipping_address"],
            "new_address": new_address, "decision": decision.decision, "reason": decision.reason,
            "message": "Delivery address updated."}
