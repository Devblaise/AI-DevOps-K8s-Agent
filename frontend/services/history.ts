// Investigation history, persisted in the InsForge `investigations` table.

import { insforge } from "@/lib/insforge";
import { Diagnosis, InvestigationEvidence } from "@/types/investigation";

export interface InvestigationRecord {
  id: string;
  created_at: string;
  user_id: string;
  context: string | null;
  namespace: string | null;
  root_cause: string | null;
  confidence: number | null;
  status: string;
  summary: string | null;
  healthy: boolean;
  // Full diagnosis payload (null for older records saved before this column existed).
  diagnosis: Diagnosis | null;
}

const TABLE = "investigations";

/** Thrown when an InsForge call fails because the session is missing/expired. */
export class SessionExpiredError extends Error {
  constructor() {
    super("Your session has expired. Please sign in again.");
    this.name = "SessionExpiredError";
  }
}

// InsForge errors carry a status and/or message; treat 401/403 (or auth-ish text) as
// an expired session so the UI can send the user back to login instead of showing a
// confusing data error.
function raise(error: unknown, fallback: string): never {
  const e = error as { status?: number; message?: string };
  const msg = (e.message ?? "").toLowerCase();
  if (
    e.status === 401 ||
    e.status === 403 ||
    msg.includes("unauthorized") ||
    msg.includes("jwt") ||
    msg.includes("token")
  ) {
    throw new SessionExpiredError();
  }
  throw new Error(e.message ?? fallback);
}

function statusFor(evidence: InvestigationEvidence): string {
  if (evidence.diagnosis_error) return "error";
  if (evidence.healthy) return "healthy";
  return "diagnosed";
}

export async function saveInvestigation(
  userId: string,
  context: string,
  namespace: string | undefined,
  evidence: InvestigationEvidence,
): Promise<void> {
  // InsForge inserts take an array of rows.
  const { error } = await insforge.database.from(TABLE).insert([
    {
      user_id: userId,
      context: context || null,
      namespace: namespace || null,
      root_cause: evidence.diagnosis?.root_cause ?? null,
      confidence: evidence.diagnosis?.confidence ?? null,
      status: statusFor(evidence),
      summary: evidence.summary,
      healthy: evidence.healthy,
      diagnosis: evidence.diagnosis,
    },
  ]);
  if (error) raise(error, "Failed to save history");
}

export async function listInvestigations(
  userId: string,
  limit = 10,
): Promise<InvestigationRecord[]> {
  const { data, error } = await insforge.database
    .from(TABLE)
    .select()
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .range(0, limit - 1);
  if (error) raise(error, "Failed to load history");
  return (data as InvestigationRecord[]) ?? [];
}
