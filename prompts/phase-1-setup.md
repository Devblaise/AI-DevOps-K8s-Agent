# Phase 1 — Project scaffold

> Run in plan mode. Show me the plan and wait for approval before writing any files.
> `CLAUDE.md` and `docs/PLAN.md` are already loaded — follow them. Do not implement
> Kubernetes or AI logic in this phase.

## Goal

Stand up an empty but runnable monorepo: FastAPI backend, Next.js frontend, Docker,
and a health endpoint. Placeholders only for everything else.

## Build

**Repo layout**

```
ai-kubernetes-agent/
  backend/   (api/ core/ kubernetes/ ai/ services/ models/)
  frontend/  (components/ services/ hooks/ types/)
  docs/
  prompts/
  docker-compose.yml
  README.md
```

**Backend**

- FastAPI app with CORS, Loguru logging, and `.env` loading (pydantic-settings).
- `GET /health` -> `{"status": "healthy", "service": "ai-kubernetes-agent"}`.
- Empty placeholder modules in `kubernetes/`, `ai/`, `services/` (e.g. `def inspect_pods(): ...`).
- Python deps managed with `uv`.

**Frontend**

- Minimal Next.js + TS + Tailwind homepage: title, subtitle, a disabled-for-now
  "Investigate Cluster" button, and a "System Status: Ready" line. Clean, plain styling.

**Env files** (`.env.example` in each)

```
# backend
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
# frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

**Docker**

- Dockerfile per app; `docker-compose.yml` mapping backend:8000 and frontend:3000.

## Out of scope

kubectl, AI, OpenRouter, InsForge, auth, realtime. None of it this phase.

## Definition of done

- `docker compose up --build` works.
- `http://localhost:3000` shows the homepage.
- `http://localhost:8000/health` returns the health JSON.