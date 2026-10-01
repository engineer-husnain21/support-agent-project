"""tickets.py -- read tickets from the tickets table."""
from app.db import get_conn


def get_ticket(ticket_id) -> dict | None:
    con = get_conn()
    try:
        row = con.execute(
            "SELECT ticket_id, customer_email, subject, body, created_at FROM tickets WHERE ticket_id = ?",
            (ticket_id,)).fetchone()
    finally:
        con.close()
    return dict(row) if row else None


def is_known_customer(email: str) -> bool:
    con = get_conn()
    try:
        row = con.execute("SELECT 1 FROM customers WHERE lower(email) = ?",
                          ((email or "").strip().lower(),)).fetchone()
    finally:
        con.close()
    return row is not None
