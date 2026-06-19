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
      className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function RootCauseCard({ evidence }: { evidence: InvestigationEvidence }) {
  // Healthy cluster — nothing to diagnose.
  if (evidence.healthy && !evidence.diagnosis) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-6">
        <h2 className="text-lg font-semibold text-green-800">No issues found</h2>
        <p className="mt-1 text-sm text-green-700">{evidence.summary}</p>
      </div>
    );
  }

  // Reasoning failed (e.g. LLM/network error) — show the evidence summary plainly.
  if (evidence.diagnosis_error || !evidence.diagnosis) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
        <h2 className="text-lg font-semibold text-amber-800">
          Diagnosis unavailable
        </h2>
        <p className="mt-1 text-sm text-amber-700">{evidence.summary}</p>
        {evidence.diagnosis_error && (
          <p className="mt-2 text-xs text-amber-600">{evidence.diagnosis_error}</p>
        )}
      </div>
    );
  }

  const d = evidence.diagnosis;

  return (
    <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
            Root cause
          </p>
          <h2 className="mt-1 text-lg font-semibold text-gray-900">{d.root_cause}</h2>
        </div>
        <div className="shrink-0 text-right">
          <span className="text-2xl font-semibold text-gray-900">{d.confidence}%</span>
          <p className="text-[11px] text-gray-400">model-reported confidence</p>
        </div>
      </div>

      <Section title="Explanation">{d.explanation}</Section>
      <Section title="Suggested fix">{d.suggested_fix}</Section>
      {d.prevention && <Section title="Prevention">{d.prevention}</Section>}

      {d.kubectl_command && (
        <div>
          <div className="mb-1 flex items-center justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
              Suggested command (read-only)
            </p>
            <CopyButton text={d.kubectl_command} />
          </div>
          <pre className="overflow-x-auto rounded-md bg-gray-900 px-3 py-2 text-xs text-gray-100">
            {d.kubectl_command}
          </pre>
        </div>
      )}

      {d.confidence_reasoning && (
        <p className="text-xs text-gray-400">{d.confidence_reasoning}</p>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
        {title}
      </p>
      <p className="mt-1 text-sm text-gray-700">{children}</p>
    </div>
  );
}
