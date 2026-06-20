// Thin client for the FastAPI backend (clusters + the SSE investigation stream).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ClustersResult {
  contexts: string[];
  /** Friendly, user-facing message when kubectl/kubeconfig couldn't be read. */
  error: string | null;
}

export async function fetchClusters(): Promise<ClustersResult> {
  const res = await fetch(`${API_BASE}/clusters`);
  if (!res.ok) {
    throw new Error(
      "Couldn't reach the backend to load clusters. Is it running?",
    );
  }
  const data = (await res.json()) as Partial<ClustersResult>;
  return { contexts: data.contexts ?? [], error: data.error ?? null };
}

export function streamUrl(context: string, namespace?: string): string {
  const params = new URLSearchParams();
  if (context) params.set("context", context);
  if (namespace) params.set("namespace", namespace);
  return `${API_BASE}/investigate/stream?${params.toString()}`;
}
