"""
demo_grounding.py -- demo case 14: "the agent drafts a reply with an amount that is not in any tool result".

The real LLM will not make this mistake on demand, so this script uses a SIMULATED LLM that deliberately writes a wrong
amount and a wrong date on its first try. The grounding check compares every order number, amount and date of the reply
with the tool results, blocks the reply, and asks for a rewrite. Say clearly in the demo that the mistake is simulated.

Run:  python demo_grounding.py              the rewrite is correct, so the ticket is auto-resolved
      python demo_grounding.py --persist    the AI keeps making the mistake, so the ticket goes to a human
Then refresh the browser at http://127.0.0.1:8000/#t214 and read the step timeline.
"""
import json
import re
import sys
from types import SimpleNamespace

from app import pipeline, tickets, tools

TICKET_ID = 214
persist = "--persist" in sys.argv

ticket = tickets.get_ticket(TICKET_ID)
if ticket is None:
    raise SystemExit("Ticket 214 does not exist. Run `python demo_cases.py` first.")
order_id = int(re.search(r"#(\d+)", ticket["body"]).group(1))
track = tools.track_shipment(order_id, ticket["customer_email"])
good_reply = (f"Hi, your order #{order_id} is {track['status'].replace('_', ' ')} with {track['carrier']}, "
              f"tracking number {track['tracking_number']}. Expected delivery: {track['expected_date']}.\n\nSupport Team")
bad_reply = (f"Hi, your order #{order_id} is with {track['carrier']} and will arrive on 2026-12-25. "
             f"We have also refunded $99.00 to your card.\n\nSupport Team")

script = [json.dumps({"intents": ["track"], "new_address": None}),
          {"tool": ("track_shipment", {"order_id": order_id})},
          bad_reply,
          bad_reply if persist else good_reply]


class SimulatedLLM:
    """Plays a fixed script: it is NOT a real model."""
    def __init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self.n = 0

    def _create(self, **kwargs):
        item = script.pop(0)
        self.n += 1
        calls = None
        if isinstance(item, dict):
            name, args = item["tool"]
            calls = [SimpleNamespace(id=f"sim_{self.n}", type="function",
                                     function=SimpleNamespace(name=name, arguments=json.dumps(args)))]
            item = None
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item, tool_calls=calls))], usage=None)


print("SIMULATED LLM: its first reply contains a wrong date (2026-12-25) and a wrong amount ($99.00).")
out = pipeline.process_ticket(TICKET_ID, client=SimulatedLLM())
print(f"Result: {out['status']} | reason: {out['reason']}")
print("Open http://127.0.0.1:8000/#t214 and refresh: the timeline shows the blocked reply and what happened next.")
