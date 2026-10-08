"""
make_holdout_set.py -- picks 40 NEW labelled tickets for a held-out check.

These tickets come from the 110 that are not in data/eval_set.json. They have never been used to improve the agent,
so the result is a fairer measurement than the first test set (on which the agent was tuned after run 1).
The draw is random but seeded, and it is done ONCE, before the held-out run. The set is never changed afterwards.

Run:  python make_holdout_set.py       (writes data/holdout_set.json)
"""
import json

from app.evalsets import PER_CATEGORY, build_set

SEED = 2027

with open("data/eval_set.json", encoding="utf-8") as f:
    used = {t["ticket_id"] for t in json.load(f)["tickets"]}

chosen = build_set(SEED, exclude_ids=used)
with open("data/holdout_set.json", "w", encoding="utf-8") as f:
    json.dump({"seed": SEED, "per_category": PER_CATEGORY, "excluded": "the 40 tickets of data/eval_set.json",
               "tickets": chosen}, f, indent=1)
print(f"Wrote data/holdout_set.json with {len(chosen)} tickets (seed {SEED}), none of them in data/eval_set.json.")
