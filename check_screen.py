"""
check_screen.py -- Part A: runs the screen over all 150 tickets and checks that it catches the right ones.
No AI is involved (no LLM calls). ticket_labels is read here for TESTING only.

Run:  python check_screen.py
"""
from app.db import get_conn
from app import screen

# The screen must catch these 5 categories (the reason must match ticket_labels)
MUST_CATCH = {"spam", "injection", "angry", "legal", "unclear"}

con = get_conn()
rows = con.execute("""SELECT t.ticket_id, t.customer_email, t.subject, t.body, l.category, l.expected_reason,
                             EXISTS(SELECT 1 FROM customers c WHERE lower(c.email)=lower(t.customer_email)) AS known
                      FROM tickets t JOIN ticket_labels l USING(ticket_id) ORDER BY t.ticket_id""").fetchall()
con.close()

wrong, caught, passed_ok = [], 0, 0
by_cat = {}
for r in rows:
    res = screen.screen(r["subject"], r["body"], bool(r["known"]))
    should_catch = r["category"] in MUST_CATCH
    ok = (res.action == "escalate" and res.reason == r["expected_reason"]) if should_catch else (res.action == "pass")
    c = by_cat.setdefault(r["category"], [0, 0])
    c[1] += 1
    if ok:
        c[0] += 1
        caught += should_catch
        passed_ok += (not should_catch)
    else:
        wrong.append((r["ticket_id"], r["category"], res.action, res.reason, r["body"][:90]))

print(f"{'category':26s} correct/total")
for cat, (a, b) in sorted(by_cat.items()):
    print(f"{cat:26s} {a}/{b}" + ("   <-- screen must catch" if cat in MUST_CATCH else ""))
print(f"\nTotal correct: {caught + passed_ok}/{len(rows)}")
if wrong:
    print("\nWrong tickets:")
    for w in wrong:
        print("  ", w)
else:
    print("No mistakes. The screen handles every ticket correctly.")
