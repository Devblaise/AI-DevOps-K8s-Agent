"""Unit tests for the kubectl executor: read-only guard + command construction."""

import json

import pytest

from app.kubernetes import executor
from app.kubernetes.executor import KubectlError, run_kubectl


@pytest.mark.parametrize("verb", ["apply", "delete", "edit", "scale", "patch", "create"])
def test_rejects_write_verbs(verb):
    with pytest.raises(KubectlError):
        run_kubectl([verb, "pod", "x"])


def test_empty_args_rejected():
    with pytest.raises(KubectlError):
        run_kubectl([])


class _FakeCompleted:
    def __init__(self, stdout="{}", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_injects_context_namespace_and_json(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout=json.dumps({"ok": True}))

    monkeypatch.setattr(executor.subprocess, "run", fake_run)
    result = run_kubectl(["get", "pods"], context="kind-demo2", namespace="prod")

    cmd = captured["cmd"]
    assert cmd[:3] == ["kubectl", "get", "pods"]
    assert "--context" in cmd and cmd[cmd.index("--context") + 1] == "kind-demo2"
    assert "--namespace" in cmd and cmd[cmd.index("--namespace") + 1] == "prod"
    assert cmd[-2:] == ["-o", "json"]
    assert result == {"ok": True}


def test_all_namespaces_flag(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompleted()

    monkeypatch.setattr(executor.subprocess, "run", fake_run)
    run_kubectl(["get", "pods"], all_namespaces=True)
    assert "--all-namespaces" in captured["cmd"]
    assert "--namespace" not in captured["cmd"]


def test_logs_is_not_json(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompleted(stdout="line1\nline2")

    monkeypatch.setattr(executor.subprocess, "run", fake_run)
    out = run_kubectl(["logs", "mypod"], output_json=False)
    assert "-o" not in captured["cmd"]
    assert out == "line1\nline2"


def test_nonzero_exit_raises(monkeypatch):
    monkeypatch.setattr(
        executor.subprocess,
        "run",
        lambda cmd, **kw: _FakeCompleted(stderr="boom", returncode=1),
    )
    with pytest.raises(KubectlError) as exc:
        run_kubectl(["get", "pods"])
    assert exc.value.returncode == 1
    assert "boom" in exc.value.stderr
