"""Investigation API — streams evidence collection over Server-Sent Events."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.kubernetes.executor import KubectlError, list_contexts
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
def clusters() -> dict[str, list[str]]:
    """List available kube contexts for the cluster picker."""
    try:
        return {"contexts": list_contexts()}
    except KubectlError:
        return {"contexts": []}
