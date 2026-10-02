"""
evalrun.py -- runs the labelled test set once and saves the scored result to reports/run_<N>.json.

Each run uses its OWN copy of the store (data/eval/run_<N>.db) made from a clean base database, so refunds made in one
run never affect another run, and your real demo store (data/store.db) is never touched.
If the LLM provider fails (for example a rate limit) the ticket is retried from a clean copy of the data.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

from app import evaluation, llm, pipeline, results, tickets
from app.db import get_conn, store_today

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _path(*parts) -> str:
    return os.path.normpath(os.path.join(ROOT, *parts))


def _rel(path: str) -> str:
    """Short path for log lines. On Windows, os.path.relpath fails when the two paths are on different drives."""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def load_eval_set(path=None) -> dict:
    with open(path or _path("data", "eval_set.json"), encoding="utf-8") as f:
        return json.load(f)


def ensure_base_db(path: str) -> None:
    """A clean store, created once and reused. It is rebuilt only when it does not exist."""
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    env = {**os.environ, "STORE_DB": path}
    subprocess.run([sys.executable, "make_mock_data.py"], cwd=ROOT, env=env, check=True, capture_output=True)


def _check_labels(eval_set: dict) -> None:
    """The evaluation set was drawn from a specific data set. Stop if the store has different tickets."""
    con = get_conn()
    try:
        for c in eval_set["tickets"]:
            row = con.execute("SELECT category, expected_outcome, order_id FROM ticket_labels WHERE ticket_id = ?",
                              (c["ticket_id"],)).fetchone()
            if (row is None or row["category"] != c["category"] or row["expected_outcome"] != c["expected_outcome"]
                    or row["order_id"] != c["order_id"]):
                raise SystemExit(f"Ticket {c['ticket_id']} in the store does not match data/eval_set.json. "
                                 f"Delete data/eval/ and run `python reset_store.py`, then try again.")
    finally:
        con.close()


def _outcome_of(ticket_id: int) -> dict:
    r = results.get_result(ticket_id)
    return {"status": r["status"], "outcome": r["outcome"], "reason": r["reason"], "reply": r["reply"],
            "reply_sent": r["reply_sent"], "priority": r["priority"]}


def run_eval(run_no: int, profile: int = 1, limit: int | None = None, resume: bool = False, client=None,
             out_dir=None, db_dir=None, retries: int = 2, pause: float = 15.0, log=print,
             stop_on_failure: bool = True) -> str:
    previous_db = os.environ.get("STORE_DB")
    try:
        return _run_eval(run_no, profile, limit, resume, client, out_dir, db_dir, retries, pause, log, stop_on_failure)
    finally:   # never leave STORE_DB pointing at an evaluation database
        if previous_db is None:
            os.environ.pop("STORE_DB", None)
        else:
            os.environ["STORE_DB"] = previous_db


def _run_eval(run_no, profile, limit, resume, client, out_dir, db_dir, retries, pause, log, stop_on_failure) -> str:
    out_dir = out_dir or _path("reports")
    db_dir = db_dir or _path("data", "eval")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)
    eval_set = load_eval_set()
    cases = eval_set["tickets"][:limit] if limit else eval_set["tickets"]
    partial = bool(limit)
    out_path = os.path.join(out_dir, f"{'dryrun' if partial else 'run'}_{run_no}.json")

    base_db = os.path.join(db_dir, "base.db")
    run_db = os.path.join(db_dir, f"run_{run_no}.db")
    snap_db = os.path.join(db_dir, "snapshot.db")
    ensure_base_db(base_db)

    previous = None
    if resume and os.path.exists(out_path) and os.path.exists(run_db):
        with open(out_path, encoding="utf-8") as f:
            previous = json.load(f)
        log(f"Resuming run {run_no}: {len(previous['tickets'])} ticket(s) already done.")
    else:
        shutil.copyfile(base_db, run_db)

    os.environ["STORE_DB"] = run_db
    _check_labels(eval_set)
    world = evaluation.build_world()

    meta = (previous or {}).get("meta") or {
        "run": run_no, "profile": profile, "model": os.environ.get("LLM_MODEL", "unknown"),
        "provider": urlparse(os.environ.get("LLM_BASE_URL", "")).netloc or "unknown",
        "started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "finished": None,
        "store_today": store_today().isoformat(), "retried_tickets": 0, "complete": False}
    done = {x["ticket_id"]: x for x in (previous or {"tickets": []})["tickets"]}

    con = get_conn()
    bodies = {r["ticket_id"]: r for r in con.execute("SELECT ticket_id, customer_email, body FROM tickets").fetchall()}
    con.close()

    def save(entries, finished=False):
        meta["complete"] = finished and not partial
        meta["finished"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if finished else None
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "tickets": entries}, f, indent=1)

    entries = list(done.values())
    stopped = False
    log(f"Run {run_no} | model {meta['model']} | {len(cases)} tickets | store: {_rel(run_db)}")
    for i, case in enumerate(cases, start=1):
        tid = case["ticket_id"]
        if tid in done:
            continue
        info = bodies[tid]
        full_case = {**case, "customer_email": info["customer_email"], "body": info["body"]}
        attempts, outcome, before, after, seconds, tokens, calls = 0, None, None, None, 0.0, 0, 0
        while True:
            attempts += 1
            shutil.copyfile(run_db, snap_db)
            before = evaluation.snapshot_orders()
            t0, u0 = time.perf_counter(), (llm.USAGE["tokens"], llm.USAGE["calls"])
            try:
                pipeline.process_ticket(tid, client=client)
            except Exception as e:   # should not happen (the pipeline catches errors), but never lose a whole run
                log(f"  ticket {tid}: unexpected {type(e).__name__}: {e}")
            seconds = time.perf_counter() - t0
            tokens, calls = llm.USAGE["tokens"] - u0[0], llm.USAGE["calls"] - u0[1]
            outcome = _outcome_of(tid) if results.get_result(tid) else {
                "status": "waiting_for_human", "outcome": "escalated", "reason": "system_unavailable",
                "reply": None, "reply_sent": False, "priority": "normal"}
            if outcome["reason"] == "system_unavailable" and attempts <= retries:
                shutil.copyfile(snap_db, run_db)          # undo anything this failed attempt changed
                log(f"  ticket {tid}: system failure, retrying in {pause:.0f}s (attempt {attempts} of {retries + 1})")
                time.sleep(pause * attempts)
                continue
            break
        if outcome["reason"] == "system_unavailable" and stop_on_failure:
            # The provider keeps failing (a rate limit or an outage). Do not record the ticket: stop here, put the
            # data back as it was before this ticket, and let the run be resumed later with --resume.
            shutil.copyfile(snap_db, run_db)
            save(entries)
            log(f"\nSTOPPED at ticket {tid}: the LLM provider keeps failing (probably its daily limit).")
            log(f"{len(entries)} ticket(s) are saved. Continue later with:  python run_eval.py --run {run_no} --resume")
            stopped = True
            break
        after = evaluation.snapshot_orders()
        scored = evaluation.evaluate(full_case, outcome, before, after, world)
        if attempts > 1:
            meta["retried_tickets"] += 1
        entry = {**case, "body": info["body"], "customer_email": info["customer_email"], **outcome, **scored,
                 "seconds": round(seconds, 2), "tokens": tokens, "llm_calls": calls, "attempts": attempts}
        entries.append(entry)
        save(entries)
        mark = {"correct": "ok   ", "safe_miss": "SAFE ", "wrong": "WRONG"}[scored["verdict"]]
        log(f"[{i:>2}/{len(cases)}] #{tid:<4} {case['category']:<24} {mark} {outcome['outcome']:<15} "
            f"{seconds:5.1f}s {tokens:>6} tokens" + ("" if scored["verdict"] == "correct" else f"  <- {scored['why'][:90]}"))
    if stopped:
        return out_path
    entries.sort(key=lambda x: x["ticket_id"])
    save(entries, finished=True)
    log(f"Saved {_rel(out_path)}")
    return out_path
