# Phase 4 — Dashboard + InsForge (auth & history)

> Run in plan mode. Show me the plan and wait for approval. Follow `CLAUDE.md` and
> `docs/PLAN.md`. Do not touch backend investigation or reasoning logic. FastAPI stays
> the orchestrator; InsForge is only auth + history.
>
> Before building, fetch InsForge's canonical setup workflow at
> https://insforge.dev/skill.md and follow it for SDK wiring.

## Goal

A minimal, professional, auth-gated dashboard that drives the existing SSE stream and
persists finished investigations.

## Build

**Auth (InsForge)**

- Email/password (and optionally Google OAuth) via the InsForge SDK.
- Protected dashboard route; only authenticated users can investigate or view history.
- Keep it minimal — no custom user management UI beyond login/logout.

**Dashboard**

- Header, a cluster picker (populated from a backend endpoint that returns
  `list_contexts()` from phase 2), and an "Investigate Cluster" button.
- On click: open the SSE stream for the chosen context and render a live checklist
  that ticks off each step event (Checking Pods -> ... -> AI Reasoning -> Root Cause Found).
- Root-cause card showing root cause, explanation, suggested fix, the kubectl command
  (read-only, with a copy button — **never a run button**), and the confidence with a
  small "model-reported" label.

**History (InsForge)**

- On a finished investigation, save: timestamp, context/namespace, root cause,
  confidence, status.
- A simple recent-investigations list/table. No filters, no charts.

**Frontend robustness**

- Handle loading, stream errors, empty/healthy result, and timeouts with plain
  user-facing messages.

## Out of scope

Changing backend logic. Realtime via InsForge (we use SSE). Complex state libraries.
Charts.

## Definition of done

- Logged-out users can't reach the dashboard.
- Picking a cluster and clicking Investigate shows the live checklist and then the
  root-cause card.
- The investigation appears in history after completion.