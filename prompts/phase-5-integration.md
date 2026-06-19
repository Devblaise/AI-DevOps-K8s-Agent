# Phase 5 — Integration, reliability & failure testing

> Run in plan mode. Show me the plan and wait for approval. Follow `CLAUDE.md` and
> `docs/PLAN.md`. This phase hardens what exists — avoid new features.

## Goal

Make the full flow feel like a product: validate end-to-end, handle failure modes
gracefully, and prove it against real induced Kubernetes failures.

## Build

**End-to-end validation**

- Walk the whole path: login -> pick cluster -> investigate -> live progress ->
  diagnosis -> saved to history. Fix any seams between phases.

**Reliability** — friendly, user-facing handling for:

- Cluster unreachable / missing or invalid kubeconfig.
- `kubectl` not installed or command failure.
- OpenRouter timeout/failure or unparseable model output.
- No unhealthy resources found (healthy cluster) — a clear positive result.
- Auth/session expiry.

No raw stack traces in the UI. Example:

```
Unable to reach the Kubernetes cluster.
Check: kubeconfig path, cluster is running, kubectl permissions.
```

**Loading & empty states**

- "Investigating cluster..." while running; the per-step checklist; and a clean
  "No critical issues detected — cluster appears healthy" state.

**Failure-scenario test harness** (`docs/test-scenarios.md` + manifests under `k8s-test/`)

Provide ready-to-apply manifests that induce each failure, plus the expected diagnosis:

1. **CrashLoopBackOff** — container exits due to a missing env var.
2. **ImagePullBackOff** — deployment references a bad image tag.
3. **OOMKilled** — memory limit set far too low.
4. **Service selector mismatch** — service selector doesn't match pod labels.

For each: the apply command, what the agent should report as root cause, and the fix.
These manifests are test fixtures — they are the only things in the repo allowed to
create broken resources, and they're applied manually by the user, never by the agent.

**Cluster picker (confirm)**

- The dashboard lists every context from the local kubeconfig and investigates the
  selected one. Verify this works with multiple contexts present.

## Definition of done

- Each of the four scenarios produces a sensible, correct root cause.
- Every failure mode above shows a friendly message rather than crashing.
- A healthy cluster shows the healthy state, not an error.