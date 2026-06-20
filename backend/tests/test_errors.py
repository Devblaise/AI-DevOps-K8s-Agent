"""Phase 5: the kubectl -> friendly-message classifier.

These assert that real-world kubectl stderr is mapped to user-facing copy and that no
raw stderr leaks through for the cases we know about.
"""

import pytest

from app.kubernetes.executor import KubectlError, friendly_message


@pytest.mark.parametrize(
    ("stderr", "expected_substring"),
    [
        # Cluster unreachable — the canonical example from the phase prompt.
        (
            "The connection to the server 127.0.0.1:6443 was refused - did you "
            "specify the right host or port?",
            "Unable to reach the Kubernetes cluster",
        ),
        ("Unable to connect to the server: dial tcp: i/o timeout", "didn't respond in time"),
        (
            "Unable to connect to the server: no such host",
            "Unable to reach the Kubernetes cluster",
        ),
        # Bad context.
        ('error: context "nope" does not exist', "context wasn't found"),
        # RBAC.
        (
            'pods is forbidden: User "x" cannot list resource "pods"',
            "Access to the cluster was denied",
        ),
        # Missing kubeconfig.
        (
            "error: no configuration has been provided, try setting KUBERNETES_MASTER",
            "No usable kubeconfig",
        ),
    ],
)
def test_friendly_message_classifies(stderr, expected_substring):
    msg = friendly_message(KubectlError(f"kubectl get failed: {stderr}", stderr=stderr))
    assert expected_substring in msg
    # Friendly copy must not leak raw stderr noise.
    assert "6443" not in msg
    assert "forbidden:" not in msg


def test_kubectl_not_installed_message():
    msg = friendly_message(KubectlError("kubectl executable not found"))
    assert "kubectl isn't installed" in msg


def test_unknown_error_falls_back_to_generic():
    msg = friendly_message(KubectlError("something totally unexpected happened"))
    assert "Something went wrong talking to the cluster" in msg
