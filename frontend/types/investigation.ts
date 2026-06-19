// TypeScript mirror of the backend evidence/diagnosis schemas
// (backend/app/models/schemas.py). Kept in sync by hand.

export interface ProblematicPod {
  name: string;
  namespace: string;
  phase: string;
  reason: string;
  container: string | null;
  restart_count: number;
  message: string | null;
  node: string | null;
  labels: Record<string, string>;
}

export interface PodEvidence {
  total: number;
  problematic_pods: ProblematicPod[];
}

export interface PodLog {
  pod: string;
  namespace: string;
  container: string | null;
  tail: number;
  notable_lines: string[];
  text: string;
  error: string | null;
}

export interface LogsEvidence {
  pods: PodLog[];
}

export interface ClusterEvent {
  namespace: string;
  type: string;
  reason: string;
  message: string;
  involved_object: string;
  count: number;
  last_seen: string | null;
}

export interface EventsEvidence {
  notable: ClusterEvent[];
}

export interface DeploymentStatus {
  name: string;
  namespace: string;
  desired: number;
  available: number;
  unavailable: number;
  healthy: boolean;
  conditions: { type: string; status: string; reason: string | null }[];
}

export interface DeploymentsEvidence {
  total: number;
  unhealthy: DeploymentStatus[];
}

export interface ServiceNetwork {
  name: string;
  namespace: string;
  selector: Record<string, string>;
  matched_pods: number;
  has_endpoints: boolean;
  issues: string[];
}

export interface NetworkEvidence {
  services_with_issues: ServiceNetwork[];
}

export interface Diagnosis {
  root_cause: string;
  explanation: string;
  suggested_fix: string;
  kubectl_command: string;
  prevention: string;
  /** Model SELF-REPORT (0-100), not a calibrated probability. */
  confidence: number;
  confidence_reasoning: string;
}

export interface InvestigationEvidence {
  pods: PodEvidence;
  logs: LogsEvidence;
  events: EventsEvidence;
  deployments: DeploymentsEvidence;
  network: NetworkEvidence;
  healthy: boolean;
  summary: string;
  diagnosis: Diagnosis | null;
  diagnosis_error: string | null;
}

// SSE step events, in the order the backend emits them.
export const STEP_EVENTS = [
  "checking_pods",
  "reading_logs",
  "analyzing_events",
  "inspecting_deployments",
  "checking_network",
  "ai_reasoning",
] as const;

export type StepEvent = (typeof STEP_EVENTS)[number];

// Human-readable labels for the live checklist.
export const STEP_LABELS: Record<StepEvent | "done", string> = {
  checking_pods: "Checking Pods",
  reading_logs: "Reading Logs",
  analyzing_events: "Analyzing Events",
  inspecting_deployments: "Inspecting Deployments",
  checking_network: "Checking Network",
  ai_reasoning: "AI Reasoning",
  done: "Root Cause Found",
};
