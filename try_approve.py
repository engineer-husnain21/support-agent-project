"""
try_approve.py -- act as the human agent: approve or reject a ticket that is waiting in the human queue.

Run:   python try_approve.py 3            (approve ticket 3)
       python try_approve.py 3 reject     (reject ticket 3)
"""
import sys
from app import human_queue, results

if len(sys.argv) < 2:
    sys.exit("Usage: python try_approve.py <ticket_id> [reject]")

tid = int(sys.argv[1])
if len(sys.argv) > 2 and sys.argv[2] == "reject":
    out = human_queue.reject(tid, rejected_by="demo_agent")
else:
    out = human_queue.approve(tid, approved_by="demo_agent")

print(out)
print("Saved result:", results.get_result(tid))
