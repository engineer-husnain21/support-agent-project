"""
evalsets.py -- draws a labelled evaluation set: a fixed number of tickets per category, chosen at random with a seed.

Rules (same as make_eval_set.py): tickets that reach the agent never share an order or a customer, so one ticket's
refund cannot change another ticket's outcome. Tickets that the screen stops before the agent never change data,
so they are not restricted. Tickets in `exclude_ids` are never chosen (used for the held-out set).
"""
import random

from app.db import get_conn

SCREENED = {"injection", "angry", "legal", "spam", "unclear"}
PER_CATEGORY = {
    "track": 6, "refund_small": 5, "refund_large": 3, "refund_expired": 3, "address_ok": 3, "address_shipped": 2,
    "no_order_number_single": 1, "no_order_number_multi": 2, "two_requests": 3, "other_persons_order": 2,
    "injection": 3, "angry": 3, "legal": 2, "spam": 1, "unclear": 1,
}   # 40 in total


def build_set(seed: int, exclude_ids=(), per_category=None) -> list:
    per_category = per_category or PER_CATEGORY
    exclude = set(exclude_ids)
    con = get_conn()
    try:
        rows = con.execute("""SELECT t.ticket_id, t.customer_email, l.category, l.expected_outcome, l.expected_reason, l.order_id
                              FROM tickets t JOIN ticket_labels l USING(ticket_id) ORDER BY t.ticket_id""").fetchall()
    finally:
        con.close()

    rng = random.Random(seed)
    used_orders, used_customers, chosen = set(), set(), []
    pools = {c: [r for r in rows if r["category"] == c and r["ticket_id"] not in exclude] for c in per_category}
    # the categories with the fewest candidates go first, so the "no shared customer" rule cannot starve them
    for category in sorted(per_category, key=lambda c: (len(pools[c]), c)):
        count = per_category[category]
        pool = pools[category]
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
            raise ValueError(f"Could not find {count} usable tickets for category {category}")
    return sorted(chosen, key=lambda c: c["ticket_id"])
