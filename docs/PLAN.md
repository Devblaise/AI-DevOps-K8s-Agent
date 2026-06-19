# PLAN.md — AI Kubernetes Troubleshooting Agent

This is the roadmap. Each phase is built in a separate Claude Code session using the
matching prompt in `prompts/`. Standing rules live in `CLAUDE.md`.

## Architecture decisions (and why)

These are the calls that the original five prompts left implicit or contradictory.
They are resolved here so a coding agent never has to guess mid-build.

### 1. Progress updates: SSE, not InsForge realtime

The original plan had `POST /investigate` return the whole diagnosis in one blocking
response (phase 3) *and* show live step-by-step progress (phase 4). A single blocking
POST cannot do both. Resolution:

- Backend exposes a streaming endpoint (`GET /investigate/stream` via Server-Sent
  Events) that emits one event per step: `checking_pods`, `reading_logs`,
  `analyzing_events`, `inspecting_deployments`, `checking_network`, `ai_reasoning`,
  `done`.
- The final `done` event carries the full diagnosis payload.
- The frontend renders the checklist from these events.
- InsForge is used only for auth and saving finished investigations.

Alternative if you prefer: write step rows to an InsForge table and subscribe via
InsForge realtime. SSE is simpler and keeps the investigation layer decoupled, so
that is the default.

### 2. LLM path: OpenRouter directly

The phrase "OpenRouter via InsForge" is ambiguous — InsForge has its own model
gateway. We call OpenRouter directly with `OPENROUTER_API_KEY`. InsForge is not in
the inference path. (Swap to InsForge's gateway later if you want a single billing
surface; it's a one-file change in the LLM client.)

### 3. kubectl over JSON, read-only, context-scoped

- Every command uses `-o json`; we parse objects, not text.
- The layer never mutates the cluster.
- Cluster selection maps to `kubectl --context <name>`; the cluster list comes from
  `kubectl config get-contexts -o name`.

### 4. Backend runs on the host during development

A containerised backend can't reach a local kind/minikube API server without extra
networking (the kubeconfig points at `127.0.0.1:<port>`, which is the host, not the
container). So: run the backend with `uv run` on the host while developing the
Kubernetes features. Keep Docker/Compose working as the packaging target, and revisit
in-container cluster access only if you later target a remote cluster.

## Open risks to watch

- **Log volume / token cost.** Fetching logs for every pod across all namespaces can
  blow the context window. Cap lines per pod and only pull logs for pods already
  flagged unhealthy.
- **Confidence theatre.** The model's "92%" is self-reported. Keep it labelled as such.
- **Empty-but-healthy clusters.** "No issues found" is a first-class result, not an
  error. Handle it explicitly so the UI doesn't look broken.

## Phases

| Phase | Goal | Definition of done |
|-------|------|--------------------|
| 1 | Project scaffold | `docker compose up --build` serves the frontend on :3000 and `GET /health` returns `{"status":"healthy"}` on :8000. No k8s/AI logic. |
| 2 | Investigation layer | `GET /investigate/stream?context=<ctx>` streams step events and returns structured evidence (pods, logs, events, deployments, network). Read-only, JSON-parsed. No AI. |
| 3 | AI reasoning | The stream's `done` event includes a diagnosis (root cause, explanation, fix, kubectl command as text, self-reported confidence) produced from the evidence. |
| 4 | Dashboard + InsForge | Auth-gated dashboard renders the live checklist, a root-cause card, a cluster picker, and a history list backed by InsForge. |
| 5 | Integration + reliability | Full flow works against real induced failures (CrashLoopBackOff, ImagePullBackOff, OOMKilled, selector mismatch). Friendly errors for unreachable cluster / missing kubeconfig / LLM failure. |

## Working agreement with the agent

For each phase: feed the phase prompt in **plan mode**, review the plan, approve,
let it build, run the definition-of-done check, commit on a `feat/phase-N-*` branch,
merge, then start the next session.