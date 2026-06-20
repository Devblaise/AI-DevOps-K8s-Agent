"""Investigation API — streams evidence collection over Server-Sent Events."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.kubernetes.executor import KubectlError, friendly_message, list_contexts
from app.services.investigation import stream_investigation

router = APIRouter()


@router.get("/investigate/stream")
async def investigate_stream(context: str | None = None, namespace: str | None = None):
    """Stream the investigation.

    Emits one event per step (``checking_pods``, ``reading_logs``, ``analyzing_events``,
    ``inspecting_deployments``, ``checking_network``) and a final ``done`` event whose
    data is the full evidence payload. With no ``namespace`` the scan is cluster-wide.
    """
    return EventSourceResponse(stream_investigation(context=context, namespace=namespace))


@router.get("/clusters")
def clusters() -> dict:
    """List available kube contexts for the cluster picker.

    Always returns 200 with a ``contexts`` list. On a kubectl/kubeconfig failure the
    list is empty and ``error`` carries friendly copy so the picker can tell "no
    clusters configured" apart from "kubectl couldn't run".
    """
    try:
        return {"contexts": list_contexts(), "error": None}
    except KubectlError as exc:
        return {"contexts": [], "error": friendly_message(exc)}
