"""
make_eval_set.py -- picks the 40 tickets of the labelled evaluation set.

The draw is random but seeded, and it is done ONCE, before any evaluation run. The set is never changed after
looking at results. The script is kept in the repo so anyone can see exactly how the 40 tickets were chosen.

Rules: a fixed number of tickets per category. Tickets that reach the agent never share an order or a customer
(so one ticket's refund cannot change the outcome of another ticket in the same run). Tickets that the screen
stops before the agent (injection, angry, legal, spam, unclear) never change any data, so they are not restricted.

Run:  python make_eval_set.py       (writes data/eval_set.json)
"""
import json
import random

from app.db import get_conn

SEED = 2026
PER_CATEGORY = {
    "track": 6, "refund_small": 5, "refund_large": 3, "refund_expired": 3, "address_ok": 3, "address_shipped": 2,
    "no_order_number_single": 1, "no_order_number_multi": 2, "two_requests": 3, "other_persons_order": 2,
    "injection": 3, "angry": 3, "legal": 2, "spam": 1, "unclear": 1,
}   # 40 in total

con = get_conn()
rows = con.execute("""SELECT t.ticket_id, t.customer_email, l.category, l.expected_outcome, l.expected_reason, l.order_id
                      FROM tickets t JOIN ticket_labels l USING(ticket_id) ORDER BY t.ticket_id""").fetchall()
con.close()

SCREENED = {"injection", "angry", "legal", "spam", "unclear"}   # stopped before the agent: they never change data

rng = random.Random(SEED)
used_orders, used_customers, chosen = set(), set(), []
for category, count in PER_CATEGORY.items():
    pool = [r for r in rows if r["category"] == category]
    rng.shuffle(pool)
    picked = 0
    for r in pool:
        if picked == count:
            break
        if category not in SCREENED:
            if (r["order_id"] is not None and r["order_id"] in used_orders) or r["customer_email"] in used_customers:
                continue
            used_orders.add(r["order_id"])
            used_customers.add(r["customer_email"])
        chosen.append({"ticket_id": r["ticket_id"], "category": category, "expected_outcome": r["expected_outcome"],
                       "expected_reason": r["expected_reason"], "order_id": r["order_id"]})
        picked += 1
    if picked < count:
        raise SystemExit(f"Could not find {count} usable tickets for category {category}")

chosen.sort(key=lambda c: c["ticket_id"])
with open("data/eval_set.json", "w", encoding="utf-8") as f:
    json.dump({"seed": SEED, "per_category": PER_CATEGORY, "tickets": chosen}, f, indent=1)
print(f"Wrote data/eval_set.json with {len(chosen)} tickets (seed {SEED}).")
