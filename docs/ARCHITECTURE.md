# Architecture

How the AI Kubernetes Agent is put together and how a single investigation flows
through it. For the *why* behind specific calls (SSE vs realtime, OpenRouter directly,
etc.) see [PLAN.md](PLAN.md); for standing rules see [CLAUDE.md](../CLAUDE.md).

> **One sentence:** a user clicks *Investigate*, the backend gathers read-only evidence
> from a cluster with `kubectl`, an LLM reasons over that evidence like a senior SRE,
> and the result is streamed back step-by-step and saved to history. There is **no**
> reconcile loop — every run is an explicit user action.

## System overview

```mermaid
flowchart LR
    user([User])

    subgraph browser["Next.js frontend (App Router)"]
        ui["Dashboard<br/>cluster picker · live checklist · root-cause card · history"]
    end

    subgraph backend["FastAPI backend (orchestrator)"]
        api["HTTP API<br/>/health · /clusters · /investigate/stream (SSE)"]
        k8s["Kubernetes layer<br/>kubectl, read-only, -o json"]
        ai["AI reasoning layer"]
    end

    cluster[("Kubernetes cluster<br/>kind / minikube / remote")]
    openrouter["OpenRouter<br/>LLM inference"]
    insforge["InsForge<br/>auth + history (Postgres)"]

    user -->|clicks Investigate| ui
    ui -->|"SSE: GET /investigate/stream"| api
    ui <-->|"login + read/write history"| insforge
    api --> k8s
    api --> ai
    k8s -->|"kubectl --context (read-only)"| cluster
    ai -->|"HTTPS + OPENROUTER_API_KEY"| openrouter

    classDef ext fill:#eef,stroke:#88a;
    class cluster,openrouter,insforge ext;
```

**Key boundaries**

- **The frontend talks to two things:** the FastAPI backend (over SSE for an
  investigation) and InsForge directly (for auth and reading/writing history). InsForge
  is *not* in the investigation path.
- **The backend talks to two things:** the cluster (via `kubectl`, strictly read-only)
  and OpenRouter (directly, with `OPENROUTER_API_KEY`). The backend has no knowledge of
  InsForge.
- **Secrets stay server-side.** `OPENROUTER_API_KEY` lives only in the backend env.

## Investigation flow (end to end)

A single click runs this sequence. The backend emits one Server-Sent Event per step so
the UI can tick off a live checklist; the final `done` event carries the full diagnosis.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant FE as Frontend
    participant API as FastAPI (SSE)
    participant K as Kubernetes layer
    participant C as Cluster (kubectl)
    participant AI as AI layer
    participant OR as OpenRouter
    participant IF as InsForge

    U->>FE: Pick cluster + click Investigate
    FE->>API: GET /investigate/stream?context&namespace

    Note over API,C: Evidence gathering (read-only, -o json)
    API->>K: fetch + classify pods
    K->>C: kubectl get pods
    API-->>FE: event: checking_pods
    API->>K: collect logs (flagged pods only)
    K->>C: kubectl logs
    API-->>FE: event: reading_logs
    API->>K: inspect events
    API-->>FE: event: analyzing_events
    API->>K: inspect deployments
    API-->>FE: event: inspecting_deployments
    API->>K: inspect network / services
    API-->>FE: event: checking_network

    API-->>FE: event: ai_reasoning
    alt Cluster healthy
        Note over API,AI: Skip the LLM — nothing to diagnose
    else Problems found
        API->>AI: diagnose(evidence)
        AI->>OR: chat completion (OPENROUTER_API_KEY)
        OR-->>AI: root cause · fix · self-reported confidence
    end

    API-->>FE: event: done (full evidence + diagnosis)
    FE->>IF: save finished investigation
    FE->>U: render root-cause card + refresh history
```

## Evidence pipeline & decision points

What happens inside the stream, including the healthy short-circuit and the failure
paths. The diagnosis is only ever **read** by the user — the agent never executes the
suggested `kubectl` command.

```mermaid
flowchart TD
    start([GET /investigate/stream]) --> pods[Check pods]
    pods --> logs[Read logs<br/>flagged pods only]
    logs --> events[Analyze events]
    events --> deps[Inspect deployments]
    deps --> net[Check network / services]
    net --> summarise{Any problems?}

    summarise -- No --> healthy["done: healthy<br/>'No issues found'"]
    summarise -- Yes --> reason["AI reasoning<br/>OpenRouter"]
    reason -- ok --> diag["done: diagnosis<br/>root cause · fix · confidence*"]
    reason -- LLM/parse error --> degraded["done: evidence + diagnosis_error<br/>'Diagnosis unavailable'"]

    pods -. kubectl/cluster failure .-> err["error event<br/>friendly message"]
    logs -. failure .-> err
    events -. failure .-> err
    deps -. failure .-> err
    net -. failure .-> err

    healthy --> save[Frontend saves to InsForge history]
    diag --> save
    degraded --> save

    classDef terminal fill:#efe,stroke:#7a7;
    classDef problem fill:#fee,stroke:#c88;
    class healthy,diag,degraded terminal;
    class err,degraded problem;
```

`*` Confidence is the **model's self-report**, not a calibrated probability — it is
labelled that way everywhere it appears.

## Reliability: failure → friendly message

Every cluster/`kubectl` failure is classified into user-facing copy in the backend; raw
stderr is logged but never shown. See [test-scenarios.md](test-scenarios.md) for how to
induce each case.

```mermaid
flowchart LR
    raw["kubectl stderr / exception"] --> cls{"friendly_message()"}
    cls --> a["kubectl not installed"]
    cls --> b["Cluster unreachable"]
    cls --> c["Missing / invalid kubeconfig"]
    cls --> d["Unknown context"]
    cls --> e["RBAC / forbidden"]
    cls --> f["Timeout"]
    cls --> g["Generic fallback"]
    a & b & c & d & e & f & g --> ev["SSE error event { message }"]
    ev --> ui["Dashboard banner<br/>(no stack traces)"]
```

## Component reference

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Frontend | [`frontend/`](../frontend) | Dashboard UI, SSE client ([`hooks/useInvestigation.ts`](../frontend/hooks/useInvestigation.ts)), InsForge auth + history ([`services/history.ts`](../frontend/services/history.ts)). |
| API / orchestrator | [`backend/app/api`](../backend/app/api), [`services/investigation.py`](../backend/app/services/investigation.py) | Routes and the step-by-step SSE stream. |
| Kubernetes layer | [`backend/app/kubernetes`](../backend/app/kubernetes) | `kubectl` executor (read-only allowlist, `-o json`) + inspectors; friendly error classifier. |
| AI layer | [`backend/app/ai`](../backend/app/ai) | OpenRouter client, prompt, and reasoner that turns evidence into a diagnosis. |
| Platform services | external | InsForge (auth + `investigations` table), OpenRouter (inference). |

## Test fixtures

The failure-scenario manifests under [`k8s-test/`](../k8s-test) intentionally create
broken resources (CrashLoopBackOff, ImagePullBackOff, OOMKilled, selector mismatch).
They are the **only** thing allowed to mutate a cluster, and they are applied **manually
by a human** — never by the agent.
