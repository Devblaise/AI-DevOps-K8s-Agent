"use client";

import { InvestigationRecord } from "@/services/history";

interface Props {
  records: InvestigationRecord[];
  loading: boolean;
  error: string | null;
  onSelect: (record: InvestigationRecord) => void;
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    diagnosed: "bg-indigo-100 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300",
    healthy: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300",
    error: "bg-amber-100 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300",
  };
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] ?? "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300"}`}
    >
      {status}
    </span>
  );
}

export function HistoryList({ records, loading, error, onSelect }: Props) {
  return (
    <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
          Recent investigations
        </h2>
        {!!records.length && (
          <span className="text-xs text-gray-400 dark:text-gray-500">
            Click a row for the full diagnosis
          </span>
        )}
      </div>

      {loading && <p className="text-sm text-gray-500 dark:text-gray-400">Loading history…</p>}
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      {!loading && !error && !records.length && (
        <p className="text-sm text-gray-500 dark:text-gray-400">No investigations yet.</p>
      )}

      {!!records.length && (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">
              <tr className="border-b border-gray-100 dark:border-gray-800">
                <th className="py-2 pr-4 font-medium">When</th>
                <th className="py-2 pr-4 font-medium">Cluster / namespace</th>
                <th className="py-2 pr-4 font-medium">Root cause</th>
                <th className="py-2 pr-4 font-medium">Confidence</th>
                <th className="py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {records.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => onSelect(r)}
                  className="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50"
                >
                  <td className="whitespace-nowrap py-2.5 pr-4 text-gray-500 dark:text-gray-400">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="py-2.5 pr-4 text-gray-700 dark:text-gray-300">
                    {r.context ?? "—"}
                    {r.namespace ? ` / ${r.namespace}` : ""}
                  </td>
                  <td className="max-w-xs truncate py-2.5 pr-4 text-gray-700 dark:text-gray-300">
                    {r.root_cause ?? "—"}
                  </td>
                  <td className="py-2.5 pr-4 text-gray-700 dark:text-gray-300">
                    {r.confidence != null ? `${r.confidence}%` : "—"}
                  </td>
                  <td className="py-2.5">
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
