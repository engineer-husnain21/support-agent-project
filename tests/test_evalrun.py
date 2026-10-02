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
