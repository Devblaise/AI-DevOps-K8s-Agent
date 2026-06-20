"""kubectl executor — the only place the investigation layer shells out to kubectl.

Standing rules (CLAUDE.md) enforced here:
- Read-only only. The verb allowlist rejects anything that could mutate the cluster
  (no apply/edit/delete/scale/patch/create/...).
- Structured output: ``-o json`` is appended for every verb that supports it. ``logs``
  is the documented exception (it has no JSON form), so it is returned as text.
- Cluster/namespace scoping via ``--context`` / ``--namespace`` (``-A`` only when the
  caller explicitly asks for cluster-wide).
- kubectl arguments never carry secrets, so logging the command is safe.
"""

import json
import subprocess

from loguru import logger

# Read-only verbs only. ``args[0]`` must be one of these or the call is rejected.
READ_VERBS = frozenset({"get", "describe", "logs", "config"})

# Verbs that do not support ``-o json``.
NO_JSON_VERBS = frozenset({"logs"})


class KubectlError(Exception):
    """Raised when a kubectl invocation fails or is disallowed."""

    def __init__(self, message: str, *, returncode: int | None = None, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


def run_kubectl(
    args: list[str],
    *,
    context: str | None = None,
    namespace: str | None = None,
    all_namespaces: bool = False,
    output_json: bool = True,
    timeout: int = 30,
):
    """Run a read-only kubectl command.

    Returns parsed JSON (dict) for json-capable verbs, or raw text for ``logs``.
    Raises :class:`KubectlError` on a disallowed verb or a non-zero exit.
    """
    if not args:
        raise KubectlError("no kubectl command given")

    verb = args[0]
    if verb not in READ_VERBS:
        raise KubectlError(
            f"refusing to run non-read-only kubectl verb: {verb!r} "
            f"(allowed: {sorted(READ_VERBS)})"
        )

    cmd = ["kubectl", *args]
    if context:
        cmd += ["--context", context]
    if all_namespaces:
        cmd += ["--all-namespaces"]
    elif namespace:
        cmd += ["--namespace", namespace]

    use_json = output_json and verb not in NO_JSON_VERBS
    if use_json:
        cmd += ["-o", "json"]

    logger.info("kubectl: {}", " ".join(cmd))

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:  # kubectl not installed
        raise KubectlError("kubectl executable not found") from exc
    except subprocess.TimeoutExpired as exc:
        raise KubectlError(f"kubectl timed out after {timeout}s") from exc

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        raise KubectlError(
            f"kubectl {verb} failed (exit {proc.returncode}): {stderr}",
            returncode=proc.returncode,
            stderr=stderr,
        )

    if use_json:
        return json.loads(proc.stdout)
    return proc.stdout


def list_contexts() -> list[str]:
    """Return the kube context names (used by the cluster picker in Phase 4)."""
    out = run_kubectl(["config", "get-contexts", "-o", "name"], output_json=False)
    return [line.strip() for line in out.splitlines() if line.strip()]


# Phase 5: map a low-level kubectl failure to a friendly, user-facing message.
# The raw stderr (which can be noisy and leak paths) is logged, never shown — the UI
# only ever sees the strings below. Ordering matters: more specific matches first.
_GENERIC_FRIENDLY = (
    "Something went wrong talking to the cluster. "
    "Check that kubectl works from your terminal, then try again."
)


def friendly_message(exc: KubectlError) -> str:
    """Translate a :class:`KubectlError` into copy safe to show a user.

    Classifies on the error text rather than exit codes because kubectl returns the
    same code (1) for very different problems. We match on stderr substrings.
    """
    text = (f"{exc} {exc.stderr}").lower()

    if "executable not found" in text:
        return (
            "kubectl isn't installed or isn't on the PATH. "
            "Install kubectl and make sure it's reachable, then try again."
        )
    if "timed out" in text or "i/o timeout" in text:
        return (
            "The cluster didn't respond in time. "
            "Check that it's running and reachable, then try again."
        )
    # Missing / empty kubeconfig.
    if (
        "no configuration has been provided" in text
        or "kubeconfig" in text
        or "no such file or directory" in text
    ):
        return (
            "No usable kubeconfig was found. "
            "Check your kubeconfig path and that it points at a valid cluster."
        )
    # Bad / unknown context.
    if "context" in text and ("does not exist" in text or "no context" in text):
        return "That cluster context wasn't found. Pick a different cluster and try again."
    # Cluster unreachable — the canonical example from the phase prompt.
    if (
        "connection refused" in text
        or "was refused" in text  # "The connection to the server ... was refused"
        or "unable to connect to the server" in text
        or "no such host" in text
        or "could not resolve" in text
        or "dial tcp" in text
        or "tls handshake" in text
    ):
        return (
            "Unable to reach the Kubernetes cluster.\n"
            "Check: kubeconfig path, cluster is running, kubectl permissions."
        )
    # RBAC / authorization.
    if "forbidden" in text or "unauthorized" in text or "you must be logged in" in text:
        return (
            "Access to the cluster was denied. "
            "Check that your kubectl credentials have permission to read these resources."
        )
    return _GENERIC_FRIENDLY
