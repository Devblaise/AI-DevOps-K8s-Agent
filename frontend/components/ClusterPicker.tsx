"use client";

import { useEffect, useState } from "react";

import { fetchClusters } from "@/services/api";

interface Props {
  context: string;
  namespace: string;
  disabled: boolean;
  onContextChange: (v: string) => void;
  onNamespaceChange: (v: string) => void;
  onInvestigate: () => void;
}

export function ClusterPicker({
  context,
  namespace,
  disabled,
  onContextChange,
  onNamespaceChange,
  onInvestigate,
}: Props) {
  const [contexts, setContexts] = useState<string[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    fetchClusters()
      .then((list) => {
        if (!active) return;
        setContexts(list);
        if (list.length && !context) onContextChange(list[0]);
      })
      .catch((err) => active && setLoadError((err as Error).message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fieldClass =
    "rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm transition-colors focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 disabled:bg-gray-100 disabled:text-gray-400 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100 dark:disabled:bg-gray-800";

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <label className="flex flex-col text-sm">
        <span className="mb-1.5 font-medium text-gray-700 dark:text-gray-300">Cluster</span>
        <select
          value={context}
          disabled={disabled || loading || !contexts.length}
          onChange={(e) => onContextChange(e.target.value)}
          className={`min-w-52 ${fieldClass}`}
        >
          {loading && <option>Loading…</option>}
          {!loading && !contexts.length && <option value="">No clusters found</option>}
          {contexts.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col text-sm">
        <span className="mb-1.5 font-medium text-gray-700 dark:text-gray-300">
          Namespace (optional)
        </span>
        <input
          type="text"
          value={namespace}
          disabled={disabled}
          placeholder="all namespaces"
          onChange={(e) => onNamespaceChange(e.target.value)}
          className={`w-44 placeholder:text-gray-400 dark:placeholder:text-gray-500 ${fieldClass}`}
        />
      </label>

      <button
        type="button"
        onClick={onInvestigate}
        disabled={disabled || !context}
        className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-indigo-500 disabled:opacity-50"
      >
        {disabled ? (
          <>
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            Investigating…
          </>
        ) : (
          "Investigate Cluster"
        )}
      </button>

      {loadError && (
        <p className="w-full text-sm text-red-600 dark:text-red-400">
          Could not load clusters: {loadError}
        </p>
      )}
    </div>
  );
}
