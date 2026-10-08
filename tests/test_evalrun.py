"""End-to-end test of the evaluation runner with the rule-based fake LLM (no internet, no tokens)."""
import json
import os

from app import evaluation, evalrun
from tests.fake_llm import SmartFakeClient


def test_runner_scores_tickets_and_leaves_the_real_store_alone(tmp_path, monkeypatch):
    real_db = os.environ.pop("STORE_DB", None)
    out_dir, db_dir = tmp_path / "reports", tmp_path / "eval"
    path = evalrun.run_eval(1, limit=6, client=SmartFakeClient(), out_dir=str(out_dir), db_dir=str(db_dir),
                            retries=0, pause=0, log=lambda *a: None)
    monkeypatch.delenv("STORE_DB", raising=False)
    data = json.load(open(path))
    assert os.path.basename(path) == "dryrun_1.json"                       # dry runs never enter the report
    assert len(data["tickets"]) == 6 and data["meta"]["complete"] is False
    for t in data["tickets"]:
        assert t["verdict"] in ("correct", "safe_miss", "wrong")
        assert t["violations"] == [] and t["fact_errors"] == []
    assert (db_dir / "base.db").exists() and (db_dir / "run_1.db").exists()
    if real_db:
        os.environ["STORE_DB"] = real_db


def test_evaluation_catches_a_reply_that_claims_a_refund_that_never_happened(tmp_path, monkeypatch):
    from tests.fake_llm import SloppyFakeClient
    path = evalrun.run_eval(1, limit=40, client=SloppyFakeClient(), out_dir=str(tmp_path / "r"), db_dir=str(tmp_path / "e"),
                            retries=0, pause=0, log=lambda *a: None)
    monkeypatch.delenv("STORE_DB", raising=False)
    data = json.load(open(path))["tickets"]
    refund_small = [t for t in data if t["category"] == "refund_small"]
    assert refund_small and all(t["verdict"] == "wrong" for t in refund_small)
    assert all("no refund was executed" in t["why"] for t in refund_small)
    others = [t for t in data if t["category"] not in ("refund_small",)]
    assert all(t["verdict"] == "correct" for t in others if t["outcome"] != "auto_resolved" or t["category"] != "refund_large")


def test_log_paths_survive_different_drives(monkeypatch):
    def different_drives(path, start):
        raise ValueError("path is on mount 'C:', start on mount 'D:'")
    monkeypatch.setattr(evalrun.os.path, "relpath", different_drives)
    assert evalrun._rel("C:\\temp\\run_1.db") == "C:\\temp\\run_1.db"


def test_store_db_variable_is_restored_after_a_run(tmp_path, monkeypatch):
    monkeypatch.setenv("STORE_DB", "keep-me.db")
    evalrun.run_eval(1, limit=2, client=SmartFakeClient(), out_dir=str(tmp_path / "r"), db_dir=str(tmp_path / "e"),
                     retries=0, pause=0, log=lambda *a: None)
    assert os.environ["STORE_DB"] == "keep-me.db"


class _AlwaysFails:
    """A provider that is down (or whose daily limit is used up)."""
    def __init__(self):
        def boom(**kwargs):
            raise ConnectionError("daily limit reached")
        from types import SimpleNamespace
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=boom))


def test_run_stops_when_the_provider_keeps_failing_and_can_be_resumed(tmp_path, monkeypatch):
    out_dir, db_dir = str(tmp_path / "r"), str(tmp_path / "e")
    kw = dict(limit=3, out_dir=out_dir, db_dir=db_dir, retries=0, pause=0, log=lambda *a: None)

    path = evalrun.run_eval(1, client=_AlwaysFails(), **kw)
    saved = json.load(open(path))
    assert saved["meta"]["complete"] is False and len(saved["tickets"]) < 3
    first_done = len(saved["tickets"])

    evalrun.run_eval(1, client=SmartFakeClient(), resume=True, **kw)      # later, the provider works again
    monkeypatch.delenv("STORE_DB", raising=False)
    done = json.load(open(path))["tickets"]
    assert len(done) == 3 and {t["ticket_id"] for t in done} == {2, 5, 9}
    assert all(t["verdict"] == "correct" for t in done)                   # nothing was damaged by the failed attempt
    assert first_done < 3


def test_keep_going_scores_failures_as_safe_misses(tmp_path):
    path = evalrun.run_eval(1, limit=2, client=_AlwaysFails(), out_dir=str(tmp_path / "r"), db_dir=str(tmp_path / "e"),
                            retries=0, pause=0, log=lambda *a: None, stop_on_failure=False)
    data = json.load(open(path))["tickets"]
    assert len(data) == 2 and data[0]["infra"] is True and data[0]["verdict"] in ("safe_miss", "correct")


def test_holdout_set_runs_into_its_own_files(tmp_path, monkeypatch):
    out_dir, db_dir = tmp_path / "r", tmp_path / "e"
    path = evalrun.run_eval(1, limit=4, client=SmartFakeClient(), out_dir=str(out_dir), db_dir=str(db_dir),
                            retries=0, pause=0, log=lambda *a: None, set_name="holdout")
    monkeypatch.delenv("STORE_DB", raising=False)
    assert os.path.basename(path) == "holdout_dryrun_1.json" and (db_dir / "holdout_run_1.db").exists()
    data = json.load(open(path))
    assert data["meta"]["set"] == "holdout"
    ids = {t["ticket_id"] for t in data["tickets"]}
    assert ids == {t["ticket_id"] for t in evalrun.load_eval_set(set_name="holdout")["tickets"][:4]}
    assert not ids & {t["ticket_id"] for t in evalrun.load_eval_set()["tickets"]}
