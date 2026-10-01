"""
human_queue.py -- what happens when a human agent clicks Approve or Reject on a waiting ticket.
The UI (Day 4) will call these two functions.
"""
from app import actions, audit, results, tickets


def approve(ticket_id: int, approved_by: str = "human_agent", edited_reply: str | None = None) -> dict:
    res = results.get_result(ticket_id)
    if not res or res["status"] != "waiting_for_human":
        return {"ok": False, "error": "ticket_not_waiting_for_human"}

    ticket = tickets.get_ticket(ticket_id)
    reply = (edited_reply or res["reply"] or "").strip()
    action = res["pending_action"]
    refund = None

    if action and action.get("type") == "refund":
        # The human approval overrides ONLY the $50 limit; every other rule is still enforced.
        refund = actions.issue_refund(action["order_id"], ticket["customer_email"],
                                      approved_by_human=True, approved_by=approved_by)
        audit.log(ticket_id, "human_refund", refund)
        if not refund["executed"]:
            return {"ok": False, "error": "refund_blocked", "detail": refund}

    if not reply:
        return {"ok": False, "error": "no_reply_to_send"}

    results.update_result(ticket_id, status="human_approved", reply=reply, reply_sent=True, handled_by=approved_by)
    audit.log(ticket_id, "human_approved", {"by": approved_by, "edited": bool(edited_reply)})
    return {"ok": True, "refund": refund, "reply": reply, "simulated": True}


def reject(ticket_id: int, rejected_by: str = "human_agent", reply: str | None = None) -> dict:
    res = results.get_result(ticket_id)
    if not res or res["status"] != "waiting_for_human":
        return {"ok": False, "error": "ticket_not_waiting_for_human"}

    ticket = tickets.get_ticket(ticket_id)
    name = tickets.get_customer_name(ticket["customer_email"])
    first = name.split()[0] if name else "there"
    reply = (reply or f"Hi {first}, we reviewed your request and unfortunately we are unable to approve it. "
                      f"If you have questions, just reply to this message.\n\nSupport Team").strip()

    results.update_result(ticket_id, status="human_rejected", reply=reply, reply_sent=True, handled_by=rejected_by)
    audit.log(ticket_id, "human_rejected", {"by": rejected_by})
    return {"ok": True, "reply": reply, "simulated": True}
