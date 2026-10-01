"""
try_part_b.py -- run the whole pipeline (Part A + Part B) on real tickets with the real LLM.

WARNING: this really changes data/store.db (a simulated refund marks the order as refunded).
Run `python reset_store.py` afterwards to get a clean store again.

Run:   python try_part_b.py            (default tickets)
       python try_part_b.py 3 9 20     (your own ticket ids)
"""
import sys
from dotenv import load_dotenv
from app import audit, pipeline, tickets

load_dotenv()
ids = [int(x) for x in sys.argv[1:]] or [2, 3, 5, 7, 12, 15]

for tid in ids:
    t = tickets.get_ticket(tid)
    print("=" * 78)
    print(f"Ticket #{tid} | {t['customer_email']}")
    print(f"  \"{t['body']}\"")
    out = pipeline.process_ticket(tid)
    print(f"  RESULT : {out['status']} | outcome={out['outcome']} | reason={out['reason']} | priority={out['priority']}")
    if out["status"] == "waiting_for_human":
        print(f"  SUMMARY: {out['summary']}")
        if out["pending_action"]:
            print(f"  PENDING: {out['pending_action']}")
        if out["reply"]:
            print("  SUGGESTED REPLY (needs approval):")
            print("    " + out["reply"].replace("\n", "\n    "))
    else:
        print("  REPLY (simulated send):")
        print("    " + out["reply"].replace("\n", "\n    "))
    print("  STEPS  :", " -> ".join(a["step"] for a in audit.get_trail(tid)[-8:]))
