# Phase 3 — AI reasoning layer

> Run in plan mode. Show me the plan and wait for approval. Follow `CLAUDE.md` and
> `docs/PLAN.md`. Extend the existing stream — do not change phase-2 evidence logic.

## Goal

Turn collected evidence into a diagnosis. The agent reasons like a senior Kubernetes
SRE: correlate logs + events + state, name a root cause, suggest a fix.

## Build

**Prompt builder** (`ai/prompt.py`)

- System prompt frames the model as a senior Kubernetes SRE.
- Injects the structured evidence (pods, logs, events, deployments, network).
- Instructs the model to return **strict JSON only** (no markdown, no prose) with:
  `root_cause`, `explanation`, `suggested_fix`, `kubectl_command` (string, for the
  user to read — not executed), `prevention`, `confidence` (0–100), `confidence_reasoning`.
- Deterministic-leaning: low temperature, concrete output, no hedging.

**LLM client** (`ai/client.py`)

- OpenRouter via HTTPX, reads `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` from env.
- Timeout, a couple of retries with backoff, clean error logging, no secret leakage.
- Parses and validates the JSON response into a Pydantic `Diagnosis` model. On
  malformed JSON, retry once, then return a typed "could not parse model output" error.

**Reasoning service**

- Correlates evidence rather than summarising logs. (e.g. pod `CrashLoopBackOff` +
  log line "DATABASE_URL missing" -> root cause is the missing env var, not "the pod
  crashed".)
- Confidence is the **model's self-report** — store it as such, label it in comments.

**Wire into the stream**

- After `checking_network`, emit an `ai_reasoning` step event, run reasoning, then
  put the `Diagnosis` in the `done` event payload alongside the evidence.

## Out of scope

Auth, history, realtime, frontend, deployment. Reasoning only.

## Definition of done

- The stream's `done` event now carries a validated `Diagnosis`.
- Feeding a missing-env CrashLoopBackOff yields a root cause naming the env var.
- An LLM/network failure produces a clean typed error, not a stack trace, and does not
  crash the stream.