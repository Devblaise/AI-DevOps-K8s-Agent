"""Prompt construction for the reasoning layer.

The system prompt frames the model as a senior Kubernetes SRE and demands strict JSON.
The user prompt injects the structured evidence, with logs trimmed to guard the
token-cost risk called out in docs/PLAN.md.
"""

from __future__ import annotations

import json

from app.models.schemas import InvestigationEvidence

# Keys the model must return — kept in lockstep with the Diagnosis model.
_DIAGNOSIS_KEYS = (
    "root_cause",
    "explanation",
    "suggested_fix",
    "kubectl_command",
    "prevention",
    "confidence",
    "confidence_reasoning",
)

SYSTEM_PROMPT = f"""\
You are a senior Site Reliability Engineer who specialises in Kubernetes. You are given
structured, read-only evidence collected from a cluster (pod states, logs, events,
deployment status, and service/network checks).

Reason like an expert: CORRELATE the signals — do not merely restate them. For example,
a pod in CrashLoopBackOff whose logs say "DATABASE_URL is not set" has a root cause of a
missing environment variable, NOT "the pod crashed". Tie the log lines and events to the
observed state and name the single most likely root cause.

Respond with STRICT JSON ONLY — no markdown, no code fences, no prose before or after.
The JSON object MUST have exactly these keys:
- "root_cause": one concise sentence naming the underlying cause.
- "explanation": how the evidence supports that root cause (reference the specific
  pods/logs/events).
- "suggested_fix": the concrete action a human should take.
- "kubectl_command": a single kubectl command (string) the USER can read and run
  themselves. It is shown as text only and is never executed automatically. Use "" if
  no single command applies.
- "prevention": how to avoid this class of problem in future.
- "confidence": an integer 0-100. This is YOUR OWN self-assessment, not a measured
  probability.
- "confidence_reasoning": one sentence explaining the confidence value.

Be concrete and avoid hedging. If the evidence is genuinely insufficient, say so in
"root_cause" and lower the confidence accordingly.\
"""


def _trim_logs(evidence_dict: dict, max_chars: int = 2000) -> None:
    """Truncate verbose log text in-place; keep the (already capped) notable lines."""
    for pod_log in evidence_dict.get("logs", {}).get("pods", []):
        text = pod_log.get("text") or ""
        if len(text) > max_chars:
            pod_log["text"] = text[:max_chars] + "\n…[truncated]"


def build_user_prompt(evidence: InvestigationEvidence) -> str:
    """Serialise evidence into the user message (diagnosis fields excluded)."""
    data = evidence.model_dump(exclude={"diagnosis", "diagnosis_error"})
    _trim_logs(data)
    evidence_json = json.dumps(data, indent=2, default=str)
    keys = ", ".join(_DIAGNOSIS_KEYS)
    return (
        "Here is the evidence collected from the cluster:\n\n"
        f"{evidence_json}\n\n"
        f"Diagnose the most likely root cause. Return strict JSON with keys: {keys}."
    )


def build_messages(evidence: InvestigationEvidence) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(evidence)},
    ]
