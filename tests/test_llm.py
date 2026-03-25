import os
import sys
import importlib
from types import SimpleNamespace

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def _import_llm_module():
    return importlib.import_module("ai_service.llm")


class _FakeCompletions:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error

    def create(self, **kwargs):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self.content)
                )
            ]
        )


class _FakeClient:
    def __init__(self, content=None, error=None):
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(content=content, error=error)
        )


def test_score_medication_openai_path_success(monkeypatch):
    """Returns parsed LLM output when OpenAI call succeeds."""
    llm = _import_llm_module()
    monkeypatch.setattr(llm.LLMScorer, "_is_valid_api_key", staticmethod(lambda: True))
    monkeypatch.setattr(
        llm,
        "client",
        _FakeClient(content='{"score": 0.92, "medication": "Metformin 500mg", "reasoning": "Most recent source and safer dose."}')
    )

    result = llm.LLMScorer.score_medication(
        {"age": 67, "conditions": ["Type 2 Diabetes"], "recent_labs": {"eGFR": 45}},
        [
            {"medication": "Metformin 500mg", "source_reliability": "high", "last_updated": "2025-01-20"},
            {"medication": "Metformin 1000mg", "source_reliability": "high", "last_updated": "2024-10-15"},
        ],
    )

    assert result["model_used"] == "gpt-3.5-turbo"
    assert result["medication"] == "Metformin 500mg"
    assert result["llm_score"] == 0.92
    assert "safer dose" in result["reasoning"]


def test_score_medication_openai_failure_uses_fallback(monkeypatch):
    """Uses structured fallback output when OpenAI call fails."""
    llm = _import_llm_module()
    monkeypatch.setattr(llm.LLMScorer, "_is_valid_api_key", staticmethod(lambda: True))
    monkeypatch.setattr(llm, "client", _FakeClient(error=RuntimeError("network error")))

    result = llm.LLMScorer.score_medication(
        {"age": 55, "conditions": [], "recent_labs": []},
        [{"medication": "Lisinopril 10mg", "source_reliability": "high", "last_updated": "2025-01-01"}],
    )

    assert result["model_used"] == "fallback"
    assert result["medication"] == "Lisinopril 10mg"
    assert 0.0 <= result["llm_score"] <= 1.0
    assert "OpenAI unavailable" in result["reasoning"]


def test_score_medication_no_key_uses_local_heuristic(monkeypatch):
    """Uses local heuristic mode when API key is unavailable."""
    llm = _import_llm_module()
    monkeypatch.setattr(llm.LLMScorer, "_is_valid_api_key", staticmethod(lambda: False))

    result = llm.LLMScorer.score_medication(
        {"age": 40, "conditions": [], "recent_labs": []},
        [{"medication": "Aspirin 81mg", "source_reliability": "medium", "last_updated": "2025-01-01"}],
    )

    assert result["model_used"] == "local-heuristic"
    assert result["medication"] == "Aspirin 81mg"
    assert 0.0 <= result["llm_score"] <= 1.0


def test_validate_safety_openai_path_success(monkeypatch):
    """Returns parsed safety JSON when OpenAI call succeeds."""
    llm = _import_llm_module()
    monkeypatch.setattr(llm.LLMScorer, "_is_valid_api_key", staticmethod(lambda: True))
    monkeypatch.setattr(
        llm,
        "client",
        _FakeClient(content='{"is_safe": true, "concerns": [], "recommendation": "Continue current dose."}')
    )

    result = llm.LLMScorer.validate_safety("Metformin 500mg", {"age": 67, "conditions": ["Type 2 Diabetes"]})

    assert result["is_safe"] is True
    assert result["concerns"] == []
    assert "Continue" in result["recommendation"]


if __name__ == "__main__":
    try:
        import pytest
    except ModuleNotFoundError:
        print("pytest is not installed for this Python interpreter.")
        print("Use the project environment:")
        print("  /Users/yesenia/Projects/ClinicalDataReconciliationEngine/venv/bin/python test_llm.py")
        raise SystemExit(1)

    try:
        import openai  # noqa: F401
    except ModuleNotFoundError:
        print("openai package is not installed for this Python interpreter.")
        print("Use the project environment:")
        print("  /Users/yesenia/Projects/ClinicalDataReconciliationEngine/venv/bin/python test_llm.py")
        raise SystemExit(1)

    raise SystemExit(pytest.main([__file__, "-v"]))
