# Phase 2 — Kubernetes investigation layer

> Run in plan mode. Show me the plan and wait for approval. Follow `CLAUDE.md` and
> `docs/PLAN.md`. Still NO AI in this phase — evidence gathering only.

## Goal

Build the layer that behaves like a junior DevOps engineer collecting evidence. It
uses `kubectl` over JSON, read-only, and streams progress as it works.

## Build

**Kubectl executor** (`kubernetes/executor.py`)

- Runs `kubectl` via `subprocess`, always with `-o json` where the command supports it.
- Accepts an optional `context` and `namespace`; injects `--context` / `--namespace`.
- Captures stdout/stderr, raises a typed error on failure, logs the command (never secrets).
- Parses JSON output into Python objects. Read-only commands only — reject anything
  that isn't `get` / `describe` / `logs` / `config`.

**Cluster discovery**

- `list_contexts()` -> parses `kubectl config get-contexts -o name`. This is what the
  UI's cluster picker will use later.

**Inspectors** (each returns a typed Pydantic model, not raw dicts)

- Pod inspector: flags `CrashLoopBackOff`, `ImagePullBackOff`, `Pending`, `Error`,
  `OOMKilled`, stuck `ContainerCreating`. Reads from pod `.status`, not text.
- Logs collector: only for pods already flagged unhealthy; `--tail` capped (e.g. 100
  lines); surface exceptions, connection failures, missing-env errors, image/startup errors.
- Events analyzer: summarises `FailedScheduling`, `BackOff`, `FailedMount`,
  `FailedPull`, `ErrImagePull`, `Unhealthy`.
- Deployment inspector: available vs unavailable replicas, rollout/condition state.
- Network inspector: service existence, selector-vs-pod-label mismatch, missing endpoints.

**Investigation service** (`services/investigation.py`)

- Orchestrates: pods -> logs -> events -> deployments -> network.
- Returns one structured payload `{pods, logs, events, deployments, network}`.

**API**

- `GET /investigate/stream?context=<ctx>&namespace=<ns>` as **Server-Sent Events**.
- Emits one event per step (`checking_pods`, `reading_logs`, `analyzing_events`,
  `inspecting_deployments`, `checking_network`), then a `done` event whose data is
  the full evidence payload.
- "No unhealthy resources found" is a valid `done` result, not an error.

## Out of scope

OpenRouter, LLM reasoning, root cause, fixes, InsForge, auth.

## Definition of done

- `GET /investigate/stream?context=<your-kind-context>` streams step events and ends
  with a structured evidence payload.
- Inducing a CrashLoopBackOff pod makes it appear in `pods.problematic_pods`.
- No write commands exist anywhere in the layer.