"""Unit tests for the AI reasoning layer (no network — the LLM client is mocked)."""

import asyncio

import pytest
from pydantic import ValidationError

from app.ai import reasoner
from app.ai.client import LLMParseError
from app.ai.prompt import build_user_prompt
from app.models.schemas import (
    Diagnosis,
    InvestigationEvidence,
    PodEvidence,
    ProblematicPod,
)

VALID_JSON = """
{
  "root_cause": "Missing DATABASE_URL env var",
  "explanation": "The pod logs show 'DATABASE_URL is not set' and it is CrashLoopBackOff.",
  "suggested_fix": "Set DATABASE_URL on the deployment.",
  "kubectl_command": "kubectl set env deploy/api DATABASE_URL=postgres://...",
  "prevention": "Validate required env vars at startup.",
  "confidence": 88,
  "confidence_reasoning": "Log line directly names the missing variable."
}
"""


# --- extract_json -----------------------------------------------------------


def test_extract_plain_json():
    assert reasoner.extract_json(VALID_JSON)["confidence"] == 88


def test_extract_fenced_json():
    fenced = f"```json\n{VALID_JSON}\n```"
    assert reasoner.extract_json(fenced)["root_cause"].startswith("Missing")


def test_extract_json_with_surrounding_prose():
    noisy = f"Sure, here is the diagnosis:\n{VALID_JSON}\nHope that helps!"
    assert reasoner.extract_json(noisy)["confidence"] == 88


def test_extract_malformed_raises():
    with pytest.raises(LLMParseError):
        reasoner.extract_json("not json at all")


# --- Diagnosis validation ---------------------------------------------------


def test_confidence_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Diagnosis(
            root_cause="x", explanation="y", suggested_fix="z", confidence=150
        )


# --- prompt -----------------------------------------------------------------


def test_user_prompt_includes_evidence():
    ev = InvestigationEvidence(
        pods=PodEvidence(
            total=1,
            problematic_pods=[
                ProblematicPod(
                    name="api", namespace="default", phase="Running",
                    reason="CrashLoopBackOff", container="api",
                )
            ],
        )
    )
    prompt_text = build_user_prompt(ev)
    assert "CrashLoopBackOff" in prompt_text
    assert "root_cause" in prompt_text  # asks for the required keys


# --- diagnose (mocked client) -----------------------------------------------


def test_diagnose_parses_valid(monkeypatch):
    async def fake_chat(messages, **kw):
        return VALID_JSON

    monkeypatch.setattr(reasoner, "chat", fake_chat)
    result = asyncio.run(reasoner.diagnose(InvestigationEvidence()))
    assert isinstance(result, Diagnosis)
    assert result.confidence == 88


def test_diagnose_retries_once_then_succeeds(monkeypatch):
    calls = {"n": 0}

    async def fake_chat(messages, **kw):
        calls["n"] += 1
        return "garbage" if calls["n"] == 1 else VALID_JSON

    monkeypatch.setattr(reasoner, "chat", fake_chat)
    result = asyncio.run(reasoner.diagnose(InvestigationEvidence()))
    assert result.confidence == 88
    assert calls["n"] == 2  # retried exactly once


def test_diagnose_raises_after_retry(monkeypatch):
    async def fake_chat(messages, **kw):
        return "still not json"

    monkeypatch.setattr(reasoner, "chat", fake_chat)
    with pytest.raises(LLMParseError):
        asyncio.run(reasoner.diagnose(InvestigationEvidence()))
