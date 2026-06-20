"use client";

import { useEffect } from "react";

import { RootCauseCard } from "@/components/RootCauseCard";
import { InvestigationRecord } from "@/services/history";
import { InvestigationEvidence } from "@/types/investigation";

// Rebuild a minimal evidence object from a stored record so we can reuse RootCauseCard.
function recordToEvidence(record: InvestigationRecord): InvestigationEvidence {
  return {
    pods: { total: 0, problematic_pods: [] },
    logs: { pods: [] },
    events: { notable: [] },
    deployments: { total: 0, unhealthy: [] },
    network: { services_with_issues: [] },
    healthy: record.healthy,
    summary: record.summary ?? "",
    diagnosis: record.diagnosis,
    diagnosis_error: record.status === "error" ? (record.summary ?? "Investigation failed") : null,
  };
}

export function DiagnosisModal({
  record,
  onClose,
}: {
  record: InvestigationRecord;
  onClose: () => void;
}) {
  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const hasDetail = record.diagnosis != null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 backdrop-blur-sm sm:p-8"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl animate-fade-in-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center justify-between">
          <div className="text-sm text-gray-300">
            <span className="font-medium text-white">
              {record.context ?? "—"}
              {record.namespace ? ` / ${record.namespace}` : ""}
            </span>
            <span className="ml-2 text-gray-400">
              {new Date(record.created_at).toLocaleString()}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-8 w-8 items-center justify-center rounded-md bg-white/10 text-white hover:bg-white/20"
          >
            ✕
          </button>
        </div>

        {hasDetail ? (
          <RootCauseCard evidence={recordToEvidence(record)} />
        ) : (
          <div className="rounded-xl border border-gray-200 bg-white p-6 text-sm text-gray-600 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300">
            <p className="font-medium text-gray-900 dark:text-white">
              No detailed diagnosis stored
            </p>
            <p className="mt-1">
              {record.summary ??
                "This investigation was recorded before full diagnoses were saved. Run a new investigation to capture full details."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
