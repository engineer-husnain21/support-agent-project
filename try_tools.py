"""
try_tools.py -- Day 2: tools aur policy ko asli database pe chala ke dekhne ke liye.
Ye sirf PARHTA hai, kuch badalta nahi.   Chalao:  python try_tools.py
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
print("Store ki aaj ki tareekh:", today)

# 1) Excel ka pehla test: "Where is my order #1042?"
show("Order 1042 track (asli malik ke email se)", tools.track_shipment(1042, owner_email(1042)))

# 2) Kisi aur ka order maango -> 'not found'
show("Order 1042 kisi AUR ke email se", tools.lookup_order(1042, owner_email(1043)))

# 3) Refund policy check (kuch badla nahi jata)
for oid, label in [(1043, "$24.99 refund (10 din)"), (1045, "$119.99 refund (6 din)")]:
    o = tools.lookup_order(oid, owner_email(oid))
    show(f"Order {oid}: {label}", policy.check_refund(o, today).to_dict())

# 4) Address change check
for oid in (1044, 1042):
    o = tools.lookup_order(oid, owner_email(oid))
    show(f"Order {oid}: address change (status={o['status']})", policy.check_address_change(o).to_dict())

# 5) Order number nahi -> email se dhoondo
show("Orders by email (order 1043 wale customer ke)", tools.find_orders_by_email(owner_email(1043)))
