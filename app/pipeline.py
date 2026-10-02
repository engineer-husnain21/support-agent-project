"""
pipeline.py -- the whole flow for one ticket:

  ticket -> screen -> intent -> find the order -> agent (tools + policy) -> grounding check -> result
                 \\__________________ anything unsafe or unclear goes to the human queue __________________/

process_ticket() always ends by saving a row in ticket_results and writing the audit log.
Replies are never really sent; they are saved with reply_sent=1 and shown as SIMULATED in the UI.
"""
import time

from app import agent, audit, escalate, intent, results, screen, tickets, tools


def _escalate(t, reason, priority="normal", intents=None, order_id=None, tools_used=None, detail=None,
              pending_action=None):
    summary = escalate.build_summary(t, reason, intents, order_id, tools_used, detail)
    reply = escalate.suggested_reply(reason, t, pending_action)
    results.save_result(t["ticket_id"], "waiting_for_human", "escalated", reason, priority, reply=reply,
                        summary=summary, pending_action=pending_action, reply_sent=False)
    audit.log(t["ticket_id"], "escalated", {"reason": reason, "priority": priority, "detail": detail})
    return {"ticket_id": t["ticket_id"], "status": "waiting_for_human", "outcome": "escalated", "reason": reason,
            "priority": priority, "reply": reply, "summary": summary, "pending_action": pending_action}


def _finish(t, status, outcome, reason, reply):
    results.save_result(t["ticket_id"], status, outcome, reason, "normal", reply=reply, reply_sent=True)
    audit.log(t["ticket_id"], "reply_sent_simulated", {"status": status, "reason": reason})
    return {"ticket_id": t["ticket_id"], "status": status, "outcome": outcome, "reason": reason,
            "priority": "normal", "reply": reply, "summary": None, "pending_action": None}


def _which_order_question(t, orders: list) -> str:
    name = tickets.get_customer_name(t["customer_email"])
    first = name.split()[0] if name else "there"
    lines = [f"- #{o['order_id']} {o['item']} (${o['amount']:.2f}, {o['status']})" for o in orders]
    return (f"Hi {first}, thanks for contacting us. We found several orders on your account:\n"
            + "\n".join(lines) + "\n\nWhich order do you need help with?\n\nSupport Team")


def process_ticket(ticket_id: int, client=None) -> dict:
    """Run the whole flow for one ticket. A ticket that is processed again starts with a fresh audit trail."""
    t = tickets.get_ticket(ticket_id)
    if t is None:
        raise ValueError(f"Ticket {ticket_id} not found")
    audit.clear(ticket_id)
    started = time.perf_counter()
    out = _process(t, client)
    results.update_result(ticket_id, duration_ms=round((time.perf_counter() - started) * 1000))
    return out


def _process(t: dict, client=None) -> dict:
    ticket_id = t["ticket_id"]
    audit.log(ticket_id, "ticket_received", {"customer_email": t["customer_email"], "subject": t["subject"]})

    # 1) Screen (no AI)
    known = tickets.is_known_customer(t["customer_email"])
    s = screen.screen(t["subject"], t["body"], known)
    audit.log(ticket_id, "screen", {**s.to_dict(), "known_sender": known})
    if s.action == "escalate":
        return _escalate(t, s.reason, priority=s.priority)

    # 2) Intent (LLM classifies, code verifies)
    i = intent.classify_intent(t["subject"], t["body"], client=client)
    audit.log(ticket_id, "intent", i)
    if not i["ok"]:
        return _escalate(t, "system_unavailable", detail=i["error"])

    # 3) Which order is this about?
    order_id = i["order_id"]
    if order_id is None:
        found = tools.find_orders_by_email(t["customer_email"])
        audit.log(ticket_id, "order_lookup_by_email", {"count": found["count"]})
        if found["count"] == 0:
            return _escalate(t, "no_orders_found", intents=i["intents"])
        if found["count"] > 1:
            reply = _which_order_question(t, found["orders"])
            return _finish(t, "asked_question", "asked_question", "multiple_orders_ask_which_one", reply)
        order_id = found["orders"][0]["order_id"]

    if i["intents"] == ["other"]:
        return _escalate(t, "unsupported_request", intents=i["intents"], order_id=order_id)

    # 4) Agent with tools (policy is enforced inside the tools)
    try:
        run = agent.run_agent(t, order_id, i["intents"], client=client)
    except Exception as e:   # e.g. the LLM provider failed or hit its rate limit in the middle of the run
        audit.log(ticket_id, "agent_error", {"error": type(e).__name__})
        return _escalate(t, "system_unavailable", intents=i["intents"], order_id=order_id,
                         detail=f"agent error: {type(e).__name__}")
    used = [e["name"] for e in run.tool_log]

    if run.tool_failed:
        return _escalate(t, "system_unavailable", intents=i["intents"], order_id=order_id, tools_used=used,
                         detail="a tool failed")
    if run.pending_refund:
        return _escalate(t, "above_auto_limit", intents=i["intents"], order_id=order_id, tools_used=used,
                         pending_action=run.pending_refund)
    if run.escalate_reason:
        return _escalate(t, "agent_escalated", intents=i["intents"], order_id=order_id, tools_used=used,
                         detail=run.escalate_reason)
    if run.step_limit_hit or not run.final_reply:
        return _escalate(t, "step_limit_reached", intents=i["intents"], order_id=order_id, tools_used=used)
    if run.ungrounded:
        return _escalate(t, "ungrounded_reply", intents=i["intents"], order_id=order_id, tools_used=used,
                         detail="; ".join(run.ungrounded))
    if run.promised_handoff:   # the agent wanted a human to follow up, so make that real instead of just promising it
        return _escalate(t, "agent_escalated", intents=i["intents"], order_id=order_id, tools_used=used,
                         detail="the agent's reply promised a human follow-up")

    # 5) Reply passed the grounding check: "send" it (simulated)
    return _finish(t, "auto_resolved", "auto_resolved", "handled_by_agent", run.final_reply)
