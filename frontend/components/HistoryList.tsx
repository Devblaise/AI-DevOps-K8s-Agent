"use client";

import { InvestigationRecord } from "@/services/history";

interface Props {
  records: InvestigationRecord[];
  loading: boolean;
  error: string | null;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    diagnosed: "bg-blue-100 text-blue-700",
    healthy: "bg-green-100 text-green-700",
    error: "bg-amber-100 text-amber-700",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? "bg-gray-100 text-gray-600"}`}
    >
      {status}
    </span>
  );
}

export function HistoryList({ records, loading, error }: Props) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold text-gray-800">Recent investigations</h2>

      {loading && <p className="text-sm text-gray-500">Loading history…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && !error && !records.length && (
        <p className="text-sm text-gray-500">No investigations yet.</p>
      )}

      {!!records.length && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-gray-400">
              <tr>
                <th className="py-2 pr-4">When</th>
                <th className="py-2 pr-4">Cluster / namespace</th>
                <th className="py-2 pr-4">Root cause</th>
                <th className="py-2 pr-4">Confidence</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.map((r) => (
                <tr key={r.id}>
                  <td className="py-2 pr-4 text-gray-500">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 pr-4 text-gray-700">
                    {r.context ?? "—"}
                    {r.namespace ? ` / ${r.namespace}` : ""}
                  </td>
                  <td className="py-2 pr-4 text-gray-700">{r.root_cause ?? "—"}</td>
                  <td className="py-2 pr-4 text-gray-700">
                    {r.confidence != null ? `${r.confidence}%` : "—"}
                  </td>
                  <td className="py-2">
                    <StatusBadge status={r.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
