"""
demo_cases.py -- creates the tickets for the 14 client-ready test cases (tickets 201 to 216).

Use it right after `python reset_store.py` and before the demo. Running it again replaces the demo tickets with fresh ones.

Run:  python demo_cases.py
"""
from app import democases

try:
    made = democases.create_demo_tickets()
except democases.DemoError as e:
    raise SystemExit(f"Could not create the demo tickets: {e}")

print(f"Created {len(made)} demo tickets. In the UI open http://127.0.0.1:8000/#t201 (newest tickets are at the top of the Inbox).\n")
for m in made:
    print(f"Case {m['case']:<3} ticket #{m['ticket_id']}  order #{m['order_id']}")
    print(f"        \"{m['body']}\"")
    print(f"        -> {m['how']}\n")
