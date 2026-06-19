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

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
      <label className="flex flex-col text-sm">
        <span className="mb-1 font-medium text-gray-700">Cluster</span>
        <select
          value={context}
          disabled={disabled || loading || !contexts.length}
          onChange={(e) => onContextChange(e.target.value)}
          className="min-w-52 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-100"
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
        <span className="mb-1 font-medium text-gray-700">Namespace (optional)</span>
        <input
          type="text"
          value={namespace}
          disabled={disabled}
          placeholder="all namespaces"
          onChange={(e) => onNamespaceChange(e.target.value)}
          className="w-44 rounded-md border border-gray-300 px-3 py-2 text-sm disabled:bg-gray-100"
        />
      </label>

      <button
        type="button"
        onClick={onInvestigate}
        disabled={disabled || !context}
        className="rounded-md bg-gray-900 px-5 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
      >
        Investigate Cluster
      </button>

      {loadError && (
        <p className="w-full text-sm text-red-600">
          Could not load clusters: {loadError}
        </p>
      )}
    </div>
  );
}
