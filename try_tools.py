"""
try_tools.py -- Day 2: run the tools and the policy against the real database.
It only READS; nothing is changed.   Run:  python try_tools.py
"""
import json
from app import tools, policy
from app.db import get_conn, store_today


def owner_email(order_id):
    con = get_conn()
    row = con.execute("SELECT c.email FROM orders o JOIN customers c USING(customer_id) WHERE o.order_id=?",
                      (order_id,)).fetchone()
    con.close()
    return row["email"]


def show(title, data):
    print(f"\n=== {title}")
    print(json.dumps(data, indent=2, default=str))


today = store_today()
print("Store date (today):", today)

# 1) First Excel test: "Where is my order #1042?"
show("Order 1042 tracking (owner's email)", tools.track_shipment(1042, owner_email(1042)))

# 2) Ask for someone else's order -> 'not found'
show("Order 1042 looked up with SOMEONE ELSE's email", tools.lookup_order(1042, owner_email(1043)))

# 3) Refund policy check (nothing is changed)
for oid, label in [(1043, "$24.99 refund (10 days)"), (1045, "$119.99 refund (6 days)")]:
    o = tools.lookup_order(oid, owner_email(oid))
    show(f"Order {oid}: {label}", policy.check_refund(o, today).to_dict())

# 4) Address change check
for oid in (1044, 1042):
    o = tools.lookup_order(oid, owner_email(oid))
    show(f"Order {oid}: address change (status={o['status']})", policy.check_address_change(o).to_dict())

# 5) No order number -> look up by email
show("Orders by email (the customer who owns order 1043)", tools.find_orders_by_email(owner_email(1043)))
