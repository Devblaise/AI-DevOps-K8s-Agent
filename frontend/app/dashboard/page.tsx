"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { ClusterPicker } from "@/components/ClusterPicker";
import { HistoryList } from "@/components/HistoryList";
import { InvestigationChecklist } from "@/components/InvestigationChecklist";
import { RootCauseCard } from "@/components/RootCauseCard";
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
    <main className="mx-auto max-w-4xl px-6 py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">AI Kubernetes Agent</h1>
          <p className="text-sm text-gray-500">On-demand cluster troubleshooting</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-500">{user?.email}</span>
          <button
            type="button"
            onClick={() => signOut()}
            className="rounded-md border border-gray-300 px-3 py-1.5 font-medium text-gray-700 hover:bg-gray-100"
          >
            Log out
          </button>
        </div>
      </header>

      <ClusterPicker
        context={context}
        namespace={namespace}
        disabled={streaming}
        onContextChange={setContext}
        onNamespaceChange={setNamespace}
        onInvestigate={() => start(context, namespace || undefined)}
      />

      {phase === "error" && (
        <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
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
        <HistoryList records={records} loading={historyLoading} error={historyError} />
      </div>
    </main>
  );
}
