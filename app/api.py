"""
api.py -- the web API and the web server for the helpdesk UI.

Run it with:  python run_server.py   (then open http://127.0.0.1:8000)

Endpoints (all JSON, under /api):
  GET  /api/tickets                  list of tickets with their display status
  GET  /api/tickets/{id}             one ticket: message, result, step timeline, customer, order, shipment
  POST /api/tickets/{id}/process     run the agent on this ticket (calls the LLM)
  POST /api/process_next?n=5         run the agent on the next n tickets that are still New
  GET  /api/queue                    tickets waiting for a human, high priority first
  POST /api/tickets/{id}/approve     human approves (optionally with an edited reply)
  POST /api/tickets/{id}/reject      human rejects
  GET  /api/stats                    dashboard numbers
  GET  /api/audit                    latest audit-log events
"""
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import audit, human_queue, intent, pipeline, results, stats, tickets, timeline, tools
from app.db import get_conn

load_dotenv()

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web")

app = FastAPI(title="POC-13 Support Ticket Agent")


@app.middleware("http")
async def no_cache_for_static(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ------------------------------------------------------------------ helpers
def display_status(status: str | None, pending_action) -> tuple[str, str]:
    """Maps the internal status to the chip shown in the UI: (key, label)."""
    if status is None:
        return "new", "New"
    if status in ("auto_resolved", "asked_question"):
        return "auto_resolved", "Auto-resolved"
    if status == "waiting_for_human":
        return ("waiting", "Waiting for human") if pending_action else ("escalated", "Escalated")
    return "human_resolved", "Human resolved"


def _display_name(name: str | None, email: str) -> str:
    return name or email.split("@")[0]


def _ticket_rows(where: str = "", params: tuple = ()) -> list[dict]:
    results.ensure_table()
    con = get_conn()
    try:
        rows = con.execute(f"""
            SELECT t.ticket_id, t.customer_email, t.subject, t.body, t.created_at, c.name AS customer_name,
                   r.status, r.outcome, r.reason, r.priority, r.pending_action, r.summary, r.reply
            FROM tickets t
            LEFT JOIN customers c ON lower(c.email) = lower(t.customer_email)
            LEFT JOIN ticket_results r ON r.ticket_id = t.ticket_id
            {where}
            ORDER BY t.created_at DESC, t.ticket_id DESC""", params).fetchall()
    finally:
        con.close()
    out = []
    for r in rows:
        key, label = display_status(r["status"], r["pending_action"])
        out.append({
            "ticket_id": r["ticket_id"], "customer_email": r["customer_email"],
            "customer_name": _display_name(r["customer_name"], r["customer_email"]),
            "subject": r["subject"], "snippet": " ".join((r["body"] or "").split())[:110],
            "created_at": r["created_at"], "status_key": key, "status_label": label,
            "reason": r["reason"], "priority": r["priority"] or "normal",
            "summary": r["summary"], "suggested_reply": r["reply"] if r["status"] == "waiting_for_human" else None,
            "processed": r["status"] is not None,
        })
    return out


def _customer_panel(email: str) -> dict:
    con = get_conn()
    try:
        c = con.execute("SELECT customer_id, name, email, address FROM customers WHERE lower(email) = lower(?)",
                        (email,)).fetchone()
        orders = []
        if c:
            orders = [dict(o) for o in con.execute(
                "SELECT order_id, item, amount, status FROM orders WHERE customer_id = ? ORDER BY order_date DESC",
                (c["customer_id"],)).fetchall()]
    finally:
        con.close()
    if not c:
        return {"known": False, "name": _display_name(None, email), "email": email, "orders": []}
    return {"known": True, "name": c["name"], "email": c["email"], "address": c["address"], "orders": orders}


# ---------------------------------------------------------------- endpoints
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/tickets")
def list_tickets():
    return _ticket_rows()


@app.get("/api/tickets/{ticket_id}")
def ticket_detail(ticket_id: int):
    t = tickets.get_ticket(ticket_id)
    if t is None:
        raise HTTPException(404, "Ticket not found")
    row = _ticket_rows("WHERE t.ticket_id = ?", (ticket_id,))[0]
    result = results.get_result(ticket_id)
    trail = audit.get_trail(ticket_id)

    customer = _customer_panel(t["customer_email"])
    ids = intent.extract_order_ids(f"{t['subject']}\n{t['body']}")
    order_id = ids[0] if ids else (customer["orders"][0]["order_id"] if len(customer["orders"]) == 1 else None)
    order = shipment = None
    order_note = None
    if order_id is not None:
        order = tools.lookup_order(order_id, t["customer_email"])
        if order.get("found"):
            shipment = tools.track_shipment(order_id, t["customer_email"])
        else:
            order_note = f"Order #{order_id} was not found on this customer's account."
            order = None

    return {
        "ticket": {**t, "customer_name": row["customer_name"]},
        "status_key": row["status_key"], "status_label": row["status_label"],
        "result": result,
        "timeline": timeline.build_timeline(trail),
        "customer": customer, "order": order, "shipment": shipment, "order_note": order_note,
    }


@app.post("/api/tickets/{ticket_id}/process")
def process(ticket_id: int):
    if tickets.get_ticket(ticket_id) is None:
        raise HTTPException(404, "Ticket not found")
    try:
        pipeline.process_ticket(ticket_id)
    except Exception as e:   # the pipeline handles LLM/tool errors itself; this is a last safety net
        raise HTTPException(500, f"Processing failed: {type(e).__name__}: {e}")
    return ticket_detail(ticket_id)


@app.post("/api/process_next")
def process_next(n: int = 5):
    n = max(1, min(n, 10))
    new_ids = [r["ticket_id"] for r in sorted(_ticket_rows(), key=lambda r: r["ticket_id"]) if not r["processed"]][:n]
    done = []
    for tid in new_ids:
        try:
            out = pipeline.process_ticket(tid)
            done.append({"ticket_id": tid, "status": out["status"], "reason": out["reason"]})
        except Exception as e:
            done.append({"ticket_id": tid, "error": f"{type(e).__name__}: {e}"})
    return {"processed": done}


@app.get("/api/queue")
def queue():
    rows = [r for r in _ticket_rows() if r["status_key"] in ("waiting", "escalated")]
    rows.sort(key=lambda r: (r["priority"] != "high", r["ticket_id"]))
    return rows


class ApproveBody(BaseModel):
    reply: str | None = None
    by: str = "human_agent"


class RejectBody(BaseModel):
    reply: str | None = None
    by: str = "human_agent"


@app.post("/api/tickets/{ticket_id}/approve")
def approve(ticket_id: int, body: ApproveBody):
    out = human_queue.approve(ticket_id, approved_by=body.by, edited_reply=body.reply)
    if not out["ok"]:
        raise HTTPException(400, out.get("error", "approve failed"))
    return ticket_detail(ticket_id)


@app.post("/api/tickets/{ticket_id}/reject")
def reject(ticket_id: int, body: RejectBody):
    out = human_queue.reject(ticket_id, rejected_by=body.by, reply=body.reply)
    if not out["ok"]:
        raise HTTPException(400, out.get("error", "reject failed"))
    return ticket_detail(ticket_id)


@app.get("/api/stats")
def get_stats():
    return stats.compute_stats()


@app.get("/api/audit")
def get_audit(limit: int = 25):
    limit = max(1, min(limit, 100))
    con = get_conn()
    try:
        has = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_log'").fetchone()
        rows = con.execute("SELECT id, ticket_id, step, detail, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
                           (limit,)).fetchall() if has else []
    finally:
        con.close()
    entries = []
    for r in rows:
        item = timeline.build_timeline([{"step": r["step"], "detail": json.loads(r["detail"]), "created_at": r["created_at"]}])[0]
        entries.append({"id": r["id"], "ticket_id": r["ticket_id"], "created_at": r["created_at"],
                        "kind": item["kind"], "title": item["title"], "detail": item["detail"]})
    return entries


# -------------------------------------------------------------- static web UI
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))
