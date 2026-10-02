"""Tests for llm.py -- provider profiles and usage counting."""
from types import SimpleNamespace

import pytest
from app import llm


def test_profile_2_copies_the_second_provider_settings(monkeypatch):
    monkeypatch.setenv("LLM2_API_KEY", "key2")
    monkeypatch.setenv("LLM2_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("LLM2_MODEL", "model-two")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    llm.use_profile(2)
    import os
    assert (os.environ["LLM_API_KEY"], os.environ["LLM_MODEL"]) == ("key2", "model-two")
    assert "LLM_REASONING_EFFORT" not in os.environ          # the 'low' setting belonged to the first model

def test_missing_second_provider_stops_with_a_clear_message(monkeypatch):
    for k in ("LLM2_API_KEY", "LLM2_BASE_URL", "LLM2_MODEL"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(SystemExit) as e:
        llm.use_profile(2)
    assert "LLM2_API_KEY" in str(e.value)

def test_profile_1_changes_nothing(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "same")
    llm.use_profile(1)
    import os
    assert os.environ["LLM_MODEL"] == "same"

def test_chat_counts_calls_and_tokens(monkeypatch):
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(choices=[], usage=SimpleNamespace(total_tokens=123)))))
    before = dict(llm.USAGE)
    llm.chat(fake, [{"role": "user", "content": "hi"}])
    assert llm.USAGE["calls"] == before["calls"] + 1 and llm.USAGE["tokens"] == before["tokens"] + 123

def test_option_rejected_by_the_model_is_retried_without_it(monkeypatch):
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    seen = []

    def create(**kw):
        seen.append("extra_body" in kw)
        if "extra_body" in kw:
            raise ValueError("unknown option")
        return SimpleNamespace(choices=[], usage=None)

    llm.chat(SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), [])
    assert seen == [True, False]
