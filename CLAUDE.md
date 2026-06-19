# CLAUDE.md

Persistent context for this project. Claude Code reads this at the start of every
session. Keep it to facts that should be true in *every* session. Phase-specific
instructions live in `prompts/`, not here.

## What we are building

An **on-demand AI Kubernetes troubleshooting agent**. A user clicks "Investigate",
the backend gathers evidence from a cluster, an LLM reasons over that evidence like
a senior SRE, and the user gets a root cause + suggested fix.

This is **NOT** a Kubernetes controller or operator. There is no reconcile loop and
nothing runs continuously against the cluster. Every investigation is triggered by
an explicit user action.

## Architecture

```
Next.js frontend
   -> FastAPI backend (orchestrator)
      -> Kubernetes investigation layer (kubectl, read-only)
      -> AI reasoning layer (OpenRouter)
   -> InsForge (auth + investigation history)
```

## Tech stack

- Backend: Python 3.12+, FastAPI, Uvicorn, Pydantic v2, HTTPX, Loguru.
- Frontend: Next.js (App Router) + TypeScript, Tailwind, Axios, React Query.
- LLM: OpenRouter (HTTP API, called directly with HTTPX).
- Platform services: InsForge (auth, Postgres-backed history).
- Local infra: Docker + Docker Compose; local clusters via kind or minikube.

## Resolved decisions (do not relitigate without asking)

- **Progress updates use SSE**, not InsForge realtime. The backend streams step
  events from a Server-Sent-Events endpoint. InsForge is used only for auth and
  history. Rationale: keeps the investigation layer free of InsForge coupling.
- **OpenRouter is called directly** via `OPENROUTER_API_KEY`. InsForge is not in
  the LLM path.
- **During Kubernetes development, run the backend on the host** (`uv run`), because
  a containerised backend cannot easily reach local kind/minikube API servers.
  Docker Compose is the packaging target, not the day-to-day dev loop.

## Standing rules (always)

- **Never break working code.** Each phase extends the previous one. If a change
  would alter behaviour from an earlier phase, stop and ask first.
- **All kubectl calls use `-o json`** and parse structured output. Never scrape
  human-readable kubectl text for status strings.
- The investigation layer is **read-only**. No `apply`, `edit`, `delete`, `scale`,
  or `patch` against the cluster, ever.
- **Never execute LLM-suggested kubectl commands.** They are displayed to the user
  as text only.
- Cluster selection = `kubectl --context <name>`. Scope by `--namespace` wherever
  possible; `-A` (all namespaces) only when explicitly investigating cluster-wide.
- The confidence score is the **model's self-report**, not a measured probability.
  Label it that way in code comments and UI copy. Do not imply calibrated accuracy.
- Secrets come from env only. Never hardcode them, never log their values.

## Conventions

- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`).
- One phase = one feature branch, merged before the next phase starts.
- Python deps via `uv`; run with `uv run` (do not manually activate venvs).
- Keep code modular and readable. This is also tutorial material — favour clarity
  over cleverness.

## Commands

```bash
# Backend (host, during k8s dev)
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Full packaged stack
docker compose up --build
```

## See also

@docs/PLAN.md for the full roadmap and per-phase definition of done.