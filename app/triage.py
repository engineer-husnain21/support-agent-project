"""
triage.py -- the Part A glue: ticket arrives -> screen -> intent -> audit log.
In Part B this grows into the agent and the reply.
"""
from app import audit, intent, screen, tickets


def triage(ticket_id: int, client=None) -> dict:
    t = tickets.get_ticket(ticket_id)
    if t is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    audit.log(ticket_id, "ticket_received", {"customer_email": t["customer_email"], "subject": t["subject"]})

    known = tickets.is_known_customer(t["customer_email"])
    s = screen.screen(t["subject"], t["body"], known)
    audit.log(ticket_id, "screen", {**s.to_dict(), "known_sender": known})

    if s.action == "escalate":
        return {"ticket_id": ticket_id, "stage": "screened_out", "screen": s.to_dict(), "intent": None}

    i = intent.classify_intent(t["subject"], t["body"], client=client)
    audit.log(ticket_id, "intent", i)
    return {"ticket_id": ticket_id, "stage": "intent_done" if i["ok"] else "intent_failed",
            "screen": s.to_dict(), "intent": i}
