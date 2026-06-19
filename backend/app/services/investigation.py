"""Investigation orchestration.

Coordinates the inspectors in order (pods -> logs -> events -> deployments -> network)
and exposes the result two ways:

- ``build_evidence`` returns the full aggregate payload (used by tests / non-streaming
  callers).
- ``stream_investigation`` is an async generator that yields one SSE event per step and
  a final ``done`` event carrying the full payload.

Still no AI this phase — this only gathers structured evidence.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from loguru import logger

from app.kubernetes import inspector
from app.kubernetes.executor import KubectlError
from app.models.schemas import InvestigationEvidence


def _summarise(evidence: InvestigationEvidence) -> tuple[bool, str]:
    """Decide whether the cluster looks healthy and a one-line summary."""
    problem_counts = {
        "problematic pods": len(evidence.pods.problematic_pods),
        "unhealthy deployments": len(evidence.deployments.unhealthy),
        "services with issues": len(evidence.network.services_with_issues),
        "warning events": len(evidence.events.notable),
    }
    parts = [f"{n} {label}" for label, n in problem_counts.items() if n]
    if not parts:
        return True, "No unhealthy resources found"
    return False, "Found " + ", ".join(parts)


def build_evidence(context=None, namespace=None) -> InvestigationEvidence:
    """Run every inspector and assemble the evidence payload (blocking)."""
    all_namespaces = namespace is None

    pods_raw = inspector.fetch_pods(context, namespace, all_namespaces)
    pods = inspector.classify_pods(pods_raw)
    logs = inspector.collect_logs(pods.problematic_pods, context=context)
    events = inspector.inspect_events(context, namespace, all_namespaces)
    deployments = inspector.inspect_deployments(context, namespace, all_namespaces)
    network = inspector.inspect_network(pods_raw, context, namespace, all_namespaces)

    evidence = InvestigationEvidence(
        pods=pods, logs=logs, events=events, deployments=deployments, network=network
    )
    evidence.healthy, evidence.summary = _summarise(evidence)
    return evidence


async def stream_investigation(context=None, namespace=None) -> AsyncIterator[dict]:
    """Yield SSE events as each step completes, then a final ``done`` event.

    Each yielded dict is ``{"event": <name>, "data": <json>}`` — the shape
    sse-starlette's EventSourceResponse expects.
    """
    all_namespaces = namespace is None
    scope = "all namespaces" if all_namespaces else f"namespace {namespace}"
    logger.info("investigation start: context={} scope={}", context or "<current>", scope)

    try:
        # 1. Pods (raw kept for the network step so we don't re-fetch).
        pods_raw = await asyncio.to_thread(
            inspector.fetch_pods, context, namespace, all_namespaces
        )
        pods = inspector.classify_pods(pods_raw)
        yield {"event": "checking_pods", "data": pods.model_dump_json()}

        # 2. Logs (only for already-flagged pods).
        logs = await asyncio.to_thread(
            inspector.collect_logs, pods.problematic_pods, context
        )
        yield {"event": "reading_logs", "data": logs.model_dump_json()}

        # 3. Events.
        events = await asyncio.to_thread(
            inspector.inspect_events, context, namespace, all_namespaces
        )
        yield {"event": "analyzing_events", "data": events.model_dump_json()}

        # 4. Deployments.
        deployments = await asyncio.to_thread(
            inspector.inspect_deployments, context, namespace, all_namespaces
        )
        yield {"event": "inspecting_deployments", "data": deployments.model_dump_json()}

        # 5. Network.
        network = await asyncio.to_thread(
            inspector.inspect_network, pods_raw, context, namespace, all_namespaces
        )
        yield {"event": "checking_network", "data": network.model_dump_json()}

        evidence = InvestigationEvidence(
            pods=pods, logs=logs, events=events, deployments=deployments, network=network
        )
        evidence.healthy, evidence.summary = _summarise(evidence)
        logger.info("investigation done: {}", evidence.summary)
        yield {"event": "done", "data": evidence.model_dump_json()}

    except KubectlError as exc:
        # Minimal error surfacing this phase; friendly handling is Phase 5.
        logger.error("investigation failed: {}", exc)
        yield {"event": "error", "data": InvestigationEvidence().model_copy(
            update={"healthy": False, "summary": f"investigation failed: {exc}"}
        ).model_dump_json()}
