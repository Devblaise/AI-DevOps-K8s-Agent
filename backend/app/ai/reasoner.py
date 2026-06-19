"""AI reasoning service.

Turns the collected evidence into a validated :class:`Diagnosis` by calling OpenRouter
and parsing strict JSON. The confidence in the result is the model's self-report, not a
calibrated probability (CLAUDE.md).
"""

from __future__ import annotations

import json
import re

from loguru import logger
from pydantic import ValidationError

from app.ai import prompt
from app.ai.client import LLMParseError, chat
from app.models.schemas import Diagnosis, InvestigationEvidence

# Matches a ```json ... ``` or ``` ... ``` fenced block.
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def extract_json(content: str) -> dict:
    """Pull a JSON object out of model output, tolerating code fences / stray prose."""
    candidate = content.strip()

    fenced = _FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        # Fall back to the first {...} span if the model added prose around it.
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end > start:
            candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise LLMParseError(f"model did not return valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMParseError("model JSON was not an object")
    return parsed


def _parse_diagnosis(content: str) -> Diagnosis:
    try:
        return Diagnosis.model_validate(extract_json(content))
    except ValidationError as exc:
        raise LLMParseError(f"model JSON did not match Diagnosis: {exc}") from exc


async def diagnose(evidence: InvestigationEvidence) -> Diagnosis:
    """Reason over the evidence; retry once on malformed output, then raise."""
    messages = prompt.build_messages(evidence)

    content = await chat(messages)
    try:
        return _parse_diagnosis(content)
    except LLMParseError as first:
        logger.warning("first diagnosis parse failed ({}); retrying once", first)
        content = await chat(messages)
        return _parse_diagnosis(content)  # propagates LLMParseError if still bad
