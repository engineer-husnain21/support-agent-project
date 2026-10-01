"""
conftest.py -- builds a throwaway copy of the database for each test and adds our own known orders to it.
The tests never touch the real data/store.db.
"""
import shutil
import sqlite3
from datetime import timedelta
from types import SimpleNamespace

import pytest
from app import db

ALICE = "alice.test@example.com"
BOB = "bob.test@example.com"


@pytest.fixture()
def store(tmp_path, monkeypatch):
    dst = tmp_path / "test_store.db"
    shutil.copy(db.DEFAULT_DB, dst)          # make_mock_data.py must have been run first
    monkeypatch.setenv("STORE_DB", str(dst))
    today = db.store_today()

    con = sqlite3.connect(dst)
    con.execute("INSERT INTO customers VALUES (9001, 'Alice Test', ?, '1 Test St, Austin, TX')", (ALICE,))
    con.execute("INSERT INTO customers VALUES (9002, 'Bob Test', ?, '2 Test St, Denver, CO')", (BOB,))

    def add(oid, cust, amount, status, delivered_days_ago=None, refunded=0, item="Test Item"):
        d = (today - timedelta(days=delivered_days_ago)).isoformat() if delivered_days_ago is not None else None
        shipped = (today - timedelta(days=(delivered_days_ago or 0) + 3)).isoformat() if status != "processing" else None
        if status == "shipped":
            shipped = (today - timedelta(days=2)).isoformat()
        con.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (oid, cust, item, 1, amount, status, "1 Test St, Austin, TX",
                     (today - timedelta(days=40)).isoformat(), shipped, d, refunded))
        if status == "delivered":
            con.execute("INSERT INTO shipments VALUES (?,?,?,?,?)", (oid, "UPS", f"TRK{oid}", "delivered", d))
        elif status == "shipped":
            con.execute("INSERT INTO shipments VALUES (?,?,?,?,?)",
                        (oid, "FedEx", f"TRK{oid}", "in_transit", (today + timedelta(days=2)).isoformat()))

    add(9001, 9001, 24.99, "delivered", 10)                # small refund, inside the window
    add(9002, 9001, 119.99, "delivered", 6)                # large refund -> human
    add(9003, 9001, 20.00, "delivered", 35)                # outside the window
    add(9004, 9001, 20.00, "delivered", 30)                # boundary: exactly 30 days (allowed)
    add(9005, 9001, 20.00, "delivered", 31)                # boundary: 31 days (denied)
    add(9006, 9001, 50.00, "delivered", 5)                 # exactly $50 (allowed)
    add(9007, 9001, 50.01, "delivered", 5)                 # $50.01 (human)
    add(9008, 9001, 30.00, "processing")                   # not shipped yet
    add(9009, 9001, 30.00, "shipped")                      # already shipped
    add(9010, 9001, 15.00, "delivered", 3, refunded=1)     # already refunded
    add(9011, 9002, 10.00, "delivered", 2)                 # Bob's order
    con.commit()
    con.close()
    return dst


class FakeClient:
    """Fake LLM client so the tests run without a network."""
    def __init__(self, content=None, exc=None):
        self.content, self.exc, self.calls = content, exc, 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        if self.exc:
            raise self.exc
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])
