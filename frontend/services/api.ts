// Thin client for the FastAPI backend (clusters + the SSE investigation stream).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function fetchClusters(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/clusters`);
  if (!res.ok) {
    throw new Error(`Failed to load clusters (${res.status})`);
  }
  const data = (await res.json()) as { contexts: string[] };
  return data.contexts ?? [];
}

export function streamUrl(context: string, namespace?: string): string {
  const params = new URLSearchParams();
  if (context) params.set("context", context);
  if (namespace) params.set("namespace", namespace);
  return `${API_BASE}/investigate/stream?${params.toString()}`;
}
