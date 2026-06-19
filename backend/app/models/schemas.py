"""Pydantic schemas for the investigation evidence payload (Phase 2).

These describe the structured evidence the investigation layer collects. No diagnosis,
root cause, or fix fields yet — those are added in Phase 3.
"""

from pydantic import BaseModel, Field

# --- Pods -------------------------------------------------------------------


class ProblematicPod(BaseModel):
    name: str
    namespace: str
    phase: str
    reason: str
    container: str | None = None
    restart_count: int = 0
    message: str | None = None
    node: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)


class PodEvidence(BaseModel):
    total: int = 0
    problematic_pods: list[ProblematicPod] = Field(default_factory=list)


# --- Logs -------------------------------------------------------------------


class PodLog(BaseModel):
    pod: str
    namespace: str
    container: str | None = None
    tail: int
    notable_lines: list[str] = Field(default_factory=list)
    text: str = ""
    error: str | None = None  # e.g. "no logs available yet"


class LogsEvidence(BaseModel):
    pods: list[PodLog] = Field(default_factory=list)


# --- Events -----------------------------------------------------------------


class ClusterEvent(BaseModel):
    namespace: str
    type: str
    reason: str
    message: str
    involved_object: str
    count: int = 1
    last_seen: str | None = None


class EventsEvidence(BaseModel):
    notable: list[ClusterEvent] = Field(default_factory=list)


# --- Deployments ------------------------------------------------------------


class DeploymentCondition(BaseModel):
    type: str
    status: str
    reason: str | None = None


class DeploymentStatus(BaseModel):
    name: str
    namespace: str
    desired: int = 0
    available: int = 0
    unavailable: int = 0
    healthy: bool = True
    conditions: list[DeploymentCondition] = Field(default_factory=list)


class DeploymentsEvidence(BaseModel):
    total: int = 0
    unhealthy: list[DeploymentStatus] = Field(default_factory=list)


# --- Network ----------------------------------------------------------------


class ServiceNetwork(BaseModel):
    name: str
    namespace: str
    selector: dict[str, str] = Field(default_factory=dict)
    matched_pods: int = 0
    has_endpoints: bool = True
    issues: list[str] = Field(default_factory=list)


class NetworkEvidence(BaseModel):
    services_with_issues: list[ServiceNetwork] = Field(default_factory=list)


# --- Aggregate --------------------------------------------------------------


class InvestigationEvidence(BaseModel):
    pods: PodEvidence = Field(default_factory=PodEvidence)
    logs: LogsEvidence = Field(default_factory=LogsEvidence)
    events: EventsEvidence = Field(default_factory=EventsEvidence)
    deployments: DeploymentsEvidence = Field(default_factory=DeploymentsEvidence)
    network: NetworkEvidence = Field(default_factory=NetworkEvidence)
    healthy: bool = True
    summary: str = "No unhealthy resources found"
