"""Kubernetes inspectors — turn read-only kubectl JSON into typed evidence.

Each concern has a **pure classifier** (parsed JSON -> Pydantic model) plus a thin
fetch wrapper that calls the executor. The classifiers carry all the logic and are
unit-tested without a cluster. Status is always read from structured ``.status`` fields,
never scraped from human-readable text (CLAUDE.md).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from loguru import logger

from app.kubernetes.executor import KubectlError, run_kubectl
from app.models.schemas import (
    ClusterEvent,
    DeploymentCondition,
    DeploymentStatus,
    DeploymentsEvidence,
    EventsEvidence,
    LogsEvidence,
    NetworkEvidence,
    PodEvidence,
    PodLog,
    ProblematicPod,
    ServiceNetwork,
)

# --- Pods -------------------------------------------------------------------

# Waiting reasons that are always a problem.
BAD_WAITING = frozenset(
    {
        "CrashLoopBackOff",
        "ImagePullBackOff",
        "ErrImagePull",
        "ErrImageNeverPull",
        "InvalidImageName",
        "CreateContainerError",
        "CreateContainerConfigError",
        "RunContainerError",
    }
)
# Waiting reasons that are only a problem if the pod has been stuck a while.
SLOW_WAITING = frozenset({"ContainerCreating", "PodInitializing"})
# Terminated reasons that indicate failure.
BAD_TERMINATED = frozenset({"OOMKilled", "Error", "ContainerCannotRun", "DeadlineExceeded"})

# How long a pod may sit Pending / ContainerCreating before we flag it.
STUCK_THRESHOLD_SECONDS = 90


def _age_seconds(timestamp: str | None, now: datetime) -> float:
    if not timestamp:
        return 0.0
    try:
        created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return (now - created).total_seconds()


def _classify_container_states(statuses: list[dict]) -> tuple[str | None, str | None, str | None, int]:
    """Return (reason, container, message, restart_count) for the first bad container."""
    restart_count = 0
    for cs in statuses:
        restart_count = max(restart_count, cs.get("restartCount", 0))
        state = cs.get("state", {})
        waiting = state.get("waiting")
        if waiting and waiting.get("reason") in BAD_WAITING:
            return waiting["reason"], cs.get("name"), waiting.get("message"), cs.get("restartCount", 0)
        terminated = state.get("terminated")
        if terminated and terminated.get("reason") in BAD_TERMINATED:
            return terminated["reason"], cs.get("name"), terminated.get("message"), cs.get("restartCount", 0)
    return None, None, None, restart_count


def classify_pods(raw: dict, now: datetime | None = None) -> PodEvidence:
    """Classify ``kubectl get pods -o json`` output into problematic pods."""
    now = now or datetime.now(timezone.utc)
    items = raw.get("items", [])
    problematic: list[ProblematicPod] = []

    for pod in items:
        meta = pod.get("metadata", {})
        spec = pod.get("spec", {})
        status = pod.get("status", {})
        phase = status.get("phase", "Unknown")

        container_statuses = (status.get("containerStatuses") or []) + (
            status.get("initContainerStatuses") or []
        )
        reason, container, message, restart_count = _classify_container_states(container_statuses)

        # Pull stuck/slow waiting reasons in only if the pod has been around a while.
        if reason is None:
            for cs in container_statuses:
                waiting = cs.get("state", {}).get("waiting")
                if waiting and waiting.get("reason") in SLOW_WAITING:
                    if _age_seconds(meta.get("creationTimestamp"), now) > STUCK_THRESHOLD_SECONDS:
                        reason = waiting["reason"]
                        container = cs.get("name")
                        message = waiting.get("message")
                    break

        # Phase-level failures.
        if reason is None and phase == "Failed":
            reason = "Failed"
            message = status.get("reason") or status.get("message")
        if reason is None and phase == "Pending":
            if _age_seconds(meta.get("creationTimestamp"), now) > STUCK_THRESHOLD_SECONDS:
                reason = "Pending"

        if reason is None:
            continue

        problematic.append(
            ProblematicPod(
                name=meta.get("name", "<unknown>"),
                namespace=meta.get("namespace", "default"),
                phase=phase,
                reason=reason,
                container=container,
                restart_count=restart_count,
                message=message,
                node=spec.get("nodeName"),
                labels=meta.get("labels", {}) or {},
            )
        )

    return PodEvidence(total=len(items), problematic_pods=problematic)


def inspect_pods(raw_or_fetch, context=None, namespace=None, all_namespaces=False) -> PodEvidence:
    """Convenience wrapper kept for symmetry; prefer fetch_pods + classify_pods."""
    raw = raw_or_fetch if isinstance(raw_or_fetch, dict) else fetch_pods(context, namespace, all_namespaces)
    return classify_pods(raw)


def fetch_pods(context=None, namespace=None, all_namespaces=False) -> dict:
    return run_kubectl(
        ["get", "pods"], context=context, namespace=namespace, all_namespaces=all_namespaces
    )


# --- Logs -------------------------------------------------------------------

NOTABLE_LOG_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"traceback",
        r"exception",
        r"\berror\b",
        r"\bfatal\b",
        r"panic",
        r"connection refused",
        r"could not connect|cannot connect|connection failed",
        r"no such host|name resolution",
        r"permission denied",
        r"image|manifest unknown|pull access denied",
        r"out of memory|oomkill",
        r"missing|not set|undefined|required.*env|environment variable",
    )
]


def extract_notable(text: str, limit: int = 20) -> list[str]:
    notable: list[str] = []
    for line in text.splitlines():
        if any(p.search(line) for p in NOTABLE_LOG_PATTERNS):
            notable.append(line.strip())
            if len(notable) >= limit:
                break
    return notable


def collect_logs(
    problematic_pods: list[ProblematicPod], context=None, tail: int = 100
) -> LogsEvidence:
    """Fetch logs only for already-flagged pods (CLAUDE.md: cap lines, target the sick)."""
    logs: list[PodLog] = []
    for pod in problematic_pods:
        args = ["logs", pod.name, "--tail", str(tail)]
        if pod.container:
            args += ["-c", pod.container]
        try:
            text = run_kubectl(
                args, context=context, namespace=pod.namespace, output_json=False
            )
            logs.append(
                PodLog(
                    pod=pod.name,
                    namespace=pod.namespace,
                    container=pod.container,
                    tail=tail,
                    notable_lines=extract_notable(text),
                    text=text,
                )
            )
        except KubectlError as exc:
            logs.append(
                PodLog(
                    pod=pod.name,
                    namespace=pod.namespace,
                    container=pod.container,
                    tail=tail,
                    error=exc.stderr or str(exc),
                )
            )
    return LogsEvidence(pods=logs)


# --- Events -----------------------------------------------------------------

NOTABLE_EVENT_REASONS = frozenset(
    {
        "FailedScheduling",
        "BackOff",
        "FailedMount",
        "FailedPull",
        "ErrImagePull",
        "Failed",
        "Unhealthy",
        "FailedCreatePodSandBox",
    }
)


def classify_events(raw: dict) -> EventsEvidence:
    notable: list[ClusterEvent] = []
    for ev in raw.get("items", []):
        reason = ev.get("reason", "")
        if reason not in NOTABLE_EVENT_REASONS and ev.get("type") != "Warning":
            continue
        obj = ev.get("involvedObject", {})
        notable.append(
            ClusterEvent(
                namespace=ev.get("metadata", {}).get("namespace", "default"),
                type=ev.get("type", "Normal"),
                reason=reason,
                message=ev.get("message", ""),
                involved_object=f"{obj.get('kind', '?')}/{obj.get('name', '?')}",
                count=ev.get("count", 1),
                last_seen=ev.get("lastTimestamp") or ev.get("eventTime"),
            )
        )
    return EventsEvidence(notable=notable)


def inspect_events(context=None, namespace=None, all_namespaces=False) -> EventsEvidence:
    raw = run_kubectl(
        ["get", "events"], context=context, namespace=namespace, all_namespaces=all_namespaces
    )
    return classify_events(raw)


# --- Deployments ------------------------------------------------------------


def classify_deployments(raw: dict) -> DeploymentsEvidence:
    items = raw.get("items", [])
    unhealthy: list[DeploymentStatus] = []
    for dep in items:
        meta = dep.get("metadata", {})
        spec = dep.get("spec", {})
        status = dep.get("status", {})
        desired = spec.get("replicas", 0)
        available = status.get("availableReplicas", 0) or 0
        unavailable = status.get("unavailableReplicas", 0) or 0

        conditions = [
            DeploymentCondition(
                type=c.get("type", ""), status=c.get("status", ""), reason=c.get("reason")
            )
            for c in status.get("conditions", [])
        ]
        healthy = available >= desired and unavailable == 0
        if healthy:
            continue
        unhealthy.append(
            DeploymentStatus(
                name=meta.get("name", "<unknown>"),
                namespace=meta.get("namespace", "default"),
                desired=desired,
                available=available,
                unavailable=unavailable,
                healthy=False,
                conditions=conditions,
            )
        )
    return DeploymentsEvidence(total=len(items), unhealthy=unhealthy)


def inspect_deployments(context=None, namespace=None, all_namespaces=False) -> DeploymentsEvidence:
    raw = run_kubectl(
        ["get", "deployments"], context=context, namespace=namespace, all_namespaces=all_namespaces
    )
    return classify_deployments(raw)


# --- Network ----------------------------------------------------------------


def _selector_matches(selector: dict, labels: dict) -> bool:
    return all(labels.get(k) == v for k, v in selector.items())


def classify_network(services_raw: dict, endpoints_raw: dict, pods_raw: dict) -> NetworkEvidence:
    """Find services whose selector matches no pods or that have no ready endpoints."""
    pods = pods_raw.get("items", [])
    # name -> bool: does this endpoints object have at least one ready address?
    endpoints_ready: dict[tuple[str, str], bool] = {}
    for ep in endpoints_raw.get("items", []):
        meta = ep.get("metadata", {})
        key = (meta.get("namespace", "default"), meta.get("name", ""))
        ready = any(subset.get("addresses") for subset in ep.get("subsets") or [])
        endpoints_ready[key] = ready

    with_issues: list[ServiceNetwork] = []
    for svc in services_raw.get("items", []):
        meta = svc.get("metadata", {})
        spec = svc.get("spec", {})
        selector = spec.get("selector") or {}
        ns = meta.get("namespace", "default")
        name = meta.get("name", "<unknown>")

        # Skip services without a selector (ExternalName / manually-managed endpoints).
        if not selector:
            continue

        matched = sum(
            1
            for pod in pods
            if pod.get("metadata", {}).get("namespace") == ns
            and _selector_matches(selector, pod.get("metadata", {}).get("labels") or {})
        )
        has_endpoints = endpoints_ready.get((ns, name), False)

        issues: list[str] = []
        if matched == 0:
            issues.append("selector matches no pods")
        if not has_endpoints:
            issues.append("no ready endpoints")

        if issues:
            with_issues.append(
                ServiceNetwork(
                    name=name,
                    namespace=ns,
                    selector=selector,
                    matched_pods=matched,
                    has_endpoints=has_endpoints,
                    issues=issues,
                )
            )
    return NetworkEvidence(services_with_issues=with_issues)


def inspect_network(pods_raw: dict, context=None, namespace=None, all_namespaces=False) -> NetworkEvidence:
    services_raw = run_kubectl(
        ["get", "services"], context=context, namespace=namespace, all_namespaces=all_namespaces
    )
    try:
        endpoints_raw = run_kubectl(
            ["get", "endpoints"], context=context, namespace=namespace, all_namespaces=all_namespaces
        )
    except KubectlError as exc:
        logger.warning("could not fetch endpoints: {}", exc)
        endpoints_raw = {"items": []}
    return classify_network(services_raw, endpoints_raw, pods_raw)
