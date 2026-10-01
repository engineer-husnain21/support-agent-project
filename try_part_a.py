"""
try_part_a.py -- run Part A on real tickets: screen + intent (LLM) + audit trail.
By default it runs 6 tickets; only 4 of them make an LLM call (keeps token usage low).

Run:   python try_part_a.py            (default tickets)
       python try_part_a.py 3 9 20     (your own ticket ids)
"""
import sys
from dotenv import load_dotenv
from app import audit, tickets, triage

load_dotenv()
ids = [int(x) for x in sys.argv[1:]] or [2, 5, 7, 11, 12, 15]

for tid in ids:
    t = tickets.get_ticket(tid)
    print("=" * 78)
    print(f"Ticket #{tid} | {t['customer_email']}")
    print(f"  \"{t['body']}\"")
    out = triage.triage(tid)
    s = out["screen"]
    print(f"  SCREEN : {s['action']} ({s['reason']}, priority={s['priority']})")
    if out["intent"]:
        i = out["intent"]
        if i["ok"]:
            print(f"  INTENT : {i['intents']} | order_id={i['order_id']} | new_address={i['new_address']}")
        else:
            print(f"  INTENT : FAILED -> {i['error']}")
    else:
        print("  INTENT : (not run: the screen stopped this ticket first, so no LLM call was made)")
    print("  AUDIT  :", " -> ".join(a["step"] for a in audit.get_trail(tid)[-3:]))
