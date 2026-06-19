"""Unit tests for the pure classifiers (no cluster needed)."""

from datetime import datetime, timezone

from app.kubernetes.inspector import (
    classify_deployments,
    classify_events,
    classify_network,
    classify_pods,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _pod(name, ns="default", phase="Running", waiting=None, terminated=None,
         restart=0, labels=None, created="2026-01-01T11:00:00Z"):
    state = {}
    if waiting:
        state["waiting"] = {"reason": waiting, "message": f"{waiting} message"}
    if terminated:
        state["terminated"] = {"reason": terminated, "message": f"{terminated} message"}
    return {
        "metadata": {"name": name, "namespace": ns, "labels": labels or {}, "creationTimestamp": created},
        "spec": {"nodeName": "node-1"},
        "status": {
            "phase": phase,
            "containerStatuses": [{"name": "app", "restartCount": restart, "state": state or {"running": {}}}],
        },
    }


def test_crashloop_pod_is_flagged():
    raw = {"items": [
        _pod("crashy", waiting="CrashLoopBackOff", restart=5),
        _pod("healthy"),
    ]}
    ev = classify_pods(raw, now=NOW)
    assert ev.total == 2
    names = {p.name for p in ev.problematic_pods}
    assert names == {"crashy"}
    crashy = ev.problematic_pods[0]
    assert crashy.reason == "CrashLoopBackOff"
    assert crashy.restart_count == 5
    assert crashy.container == "app"


def test_imagepull_and_oom_flagged():
    raw = {"items": [
        _pod("imgpull", waiting="ImagePullBackOff"),
        _pod("oom", terminated="OOMKilled"),
    ]}
    reasons = {p.reason for p in classify_pods(raw, now=NOW).problematic_pods}
    assert reasons == {"ImagePullBackOff", "OOMKilled"}


def test_fresh_containercreating_not_flagged_but_stuck_is():
    fresh = _pod("fresh", phase="Pending", waiting="ContainerCreating",
                 created="2026-01-01T11:59:30Z")  # 30s old
    stuck = _pod("stuck", phase="Pending", waiting="ContainerCreating",
                 created="2026-01-01T11:00:00Z")  # 1h old
    ev = classify_pods({"items": [fresh, stuck]}, now=NOW)
    assert {p.name for p in ev.problematic_pods} == {"stuck"}


def test_deployment_unhealthy_when_replicas_unavailable():
    raw = {"items": [
        {"metadata": {"name": "web", "namespace": "default"},
         "spec": {"replicas": 3},
         "status": {"availableReplicas": 1, "unavailableReplicas": 2,
                    "conditions": [{"type": "Available", "status": "False", "reason": "MinimumReplicasUnavailable"}]}},
        {"metadata": {"name": "ok", "namespace": "default"},
         "spec": {"replicas": 2}, "status": {"availableReplicas": 2}},
    ]}
    ev = classify_deployments(raw)
    assert ev.total == 2
    assert [d.name for d in ev.unhealthy] == ["web"]
    assert ev.unhealthy[0].unavailable == 2


def test_events_filtered_to_notable():
    raw = {"items": [
        {"reason": "FailedScheduling", "type": "Warning", "message": "no nodes",
         "involvedObject": {"kind": "Pod", "name": "p1"}, "metadata": {"namespace": "default"}},
        {"reason": "Scheduled", "type": "Normal", "message": "ok",
         "involvedObject": {"kind": "Pod", "name": "p2"}, "metadata": {"namespace": "default"}},
    ]}
    ev = classify_events(raw)
    assert [e.reason for e in ev.notable] == ["FailedScheduling"]


def test_network_selector_mismatch_flagged():
    services = {"items": [{
        "metadata": {"name": "svc", "namespace": "default"},
        "spec": {"selector": {"app": "web"}},
    }]}
    pods = {"items": [
        {"metadata": {"namespace": "default", "labels": {"app": "api"}}},  # wrong label
    ]}
    endpoints = {"items": []}
    ev = classify_network(services, endpoints, pods)
    assert len(ev.services_with_issues) == 1
    issues = ev.services_with_issues[0].issues
    assert "selector matches no pods" in issues
    assert "no ready endpoints" in issues


def test_network_healthy_service_not_flagged():
    services = {"items": [{
        "metadata": {"name": "svc", "namespace": "default"},
        "spec": {"selector": {"app": "web"}},
    }]}
    pods = {"items": [{"metadata": {"namespace": "default", "labels": {"app": "web"}}}]}
    endpoints = {"items": [{"metadata": {"namespace": "default", "name": "svc"},
                            "subsets": [{"addresses": [{"ip": "10.0.0.1"}]}]}]}
    ev = classify_network(services, endpoints, pods)
    assert ev.services_with_issues == []
