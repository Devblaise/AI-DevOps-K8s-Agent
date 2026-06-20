"use client";

import { useState } from "react";

import { InvestigationEvidence } from "@/types/investigation";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-100 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
    >
      {copied ? "Copied ✓" : "Copy"}
    </button>
  );
}

export function RootCauseCard({ evidence }: { evidence: InvestigationEvidence }) {
  // Healthy cluster — nothing to diagnose.
  if (evidence.healthy && !evidence.diagnosis) {
    return (
      <div className="animate-fade-in-up rounded-xl border border-emerald-200 bg-emerald-50 p-6 dark:border-emerald-900/50 dark:bg-emerald-950/30">
        <h2 className="text-lg font-semibold text-emerald-800 dark:text-emerald-300">
          No issues found
        </h2>
        <p className="mt-1 text-sm text-emerald-700 dark:text-emerald-400">
          {evidence.summary}
        </p>
      </div>
    );
  }

  // Reasoning failed (e.g. LLM/network error) — show the evidence summary plainly.
  if (evidence.diagnosis_error || !evidence.diagnosis) {
    return (
      <div className="animate-fade-in-up rounded-xl border border-amber-200 bg-amber-50 p-6 dark:border-amber-900/50 dark:bg-amber-950/30">
        <h2 className="text-lg font-semibold text-amber-800 dark:text-amber-300">
          Diagnosis unavailable
        </h2>
        <p className="mt-1 text-sm text-amber-700 dark:text-amber-400">{evidence.summary}</p>
        {evidence.diagnosis_error && (
          <p className="mt-2 text-xs text-amber-600 dark:text-amber-500">
            {evidence.diagnosis_error}
          </p>
        )}
      </div>
    );
  }

  const d = evidence.diagnosis;
  const confColor =
    d.confidence >= 75
      ? "text-emerald-600 dark:text-emerald-400"
      : d.confidence >= 40
        ? "text-amber-600 dark:text-amber-400"
        : "text-red-600 dark:text-red-400";

  return (
    <div className="animate-fade-in-up space-y-5 rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="flex items-start justify-between gap-4 border-b border-gray-100 pb-4 dark:border-gray-800">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-indigo-500 dark:text-indigo-400">
            Root cause
          </p>
          <h2 className="mt-1 text-lg font-semibold text-gray-900 dark:text-white">
            {d.root_cause}
          </h2>
        </div>
        <div className="shrink-0 text-right">
          <span className={`text-2xl font-bold ${confColor}`}>{d.confidence}%</span>
          <p className="text-[11px] text-gray-400 dark:text-gray-500">model-reported</p>
        </div>
      </div>

      <Section title="Explanation">{d.explanation}</Section>
      <Section title="Suggested fix">{d.suggested_fix}</Section>
      {d.prevention && <Section title="Prevention">{d.prevention}</Section>}

      {d.kubectl_command && (
        <div>
          <div className="mb-1.5 flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
              Suggested command (read-only)
            </p>
            <CopyButton text={d.kubectl_command} />
          </div>
          <pre className="overflow-x-auto rounded-lg border border-gray-800 bg-gray-900 px-3.5 py-2.5 text-xs text-gray-100 dark:border-gray-700 dark:bg-gray-950">
            {d.kubectl_command}
          </pre>
        </div>
      )}

      {d.confidence_reasoning && (
        <p className="text-xs italic text-gray-400 dark:text-gray-500">
          {d.confidence_reasoning}
        </p>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
        {title}
      </p>
      <p className="mt-1 text-sm leading-relaxed text-gray-700 dark:text-gray-300">
        {children}
      </p>
    </div>
  );
}
