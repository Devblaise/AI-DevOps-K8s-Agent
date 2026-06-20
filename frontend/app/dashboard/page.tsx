"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { ClusterPicker } from "@/components/ClusterPicker";
import { DiagnosisModal } from "@/components/DiagnosisModal";
import { HistoryList } from "@/components/HistoryList";
import { InvestigationChecklist } from "@/components/InvestigationChecklist";
import { RootCauseCard } from "@/components/RootCauseCard";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useInvestigation } from "@/hooks/useInvestigation";
import {
  InvestigationRecord,
  listInvestigations,
  saveInvestigation,
} from "@/services/history";
import { InvestigationEvidence } from "@/types/investigation";

export default function DashboardPage() {
  const { user, signOut } = useAuth();
  const { phase, completedSteps, evidence, error, start } = useInvestigation();

  const [context, setContext] = useState("");
  const [namespace, setNamespace] = useState("");

  const [records, setRecords] = useState<InvestigationRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selected, setSelected] = useState<InvestigationRecord | null>(null);

  const refreshHistory = useCallback(async () => {
    if (!user) return;
    setHistoryError(null);
    try {
      setRecords(await listInvestigations(user.id));
    } catch (err) {
      setHistoryError((err as Error).message);
    } finally {
      setHistoryLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void refreshHistory();
  }, [refreshHistory]);

  // Persist each finished investigation exactly once, then refresh the list.
  const savedRef = useRef<InvestigationEvidence | null>(null);
  useEffect(() => {
    if (phase !== "done" || !evidence || !user) return;
    if (savedRef.current === evidence) return;
    savedRef.current = evidence;
    saveInvestigation(user.id, context, namespace || undefined, evidence)
      .then(refreshHistory)
      .catch((err) => setHistoryError((err as Error).message));
  }, [phase, evidence, user, context, namespace, refreshHistory]);

  const streaming = phase === "streaming";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-gray-200 bg-white/80 backdrop-blur dark:border-gray-800 dark:bg-gray-950/80">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-3.5">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2 3 7v10l9 5 9-5V7l-9-5z" />
                <path d="m3 7 9 5 9-5M12 12v10" />
              </svg>
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight text-gray-900 dark:text-white">
                AI Kubernetes Agent
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                On-demand cluster troubleshooting
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2.5 text-sm">
            <span className="hidden text-gray-500 dark:text-gray-400 sm:inline">
              {user?.email}
            </span>
            <ThemeToggle />
            <button
              type="button"
              onClick={() => signOut()}
              className="rounded-md border border-gray-200 px-3 py-1.5 font-medium text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <ClusterPicker
          context={context}
          namespace={namespace}
          disabled={streaming}
          onContextChange={setContext}
          onNamespaceChange={setNamespace}
          onInvestigate={() => start(context, namespace || undefined)}
        />

        {phase === "error" && (
          <p className="mt-4 animate-fade-in-up rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-400">
            {error}
          </p>
        )}

        {(streaming || phase === "done") && (
          <div className="mt-6 space-y-6">
            <InvestigationChecklist completedSteps={completedSteps} done={phase === "done"} />
            {phase === "done" && evidence && <RootCauseCard evidence={evidence} />}
          </div>
        )}

        <div className="mt-10">
          <HistoryList
            records={records}
            loading={historyLoading}
            error={historyError}
            onSelect={setSelected}
          />
        </div>
      </main>

      {selected && (
        <DiagnosisModal record={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
