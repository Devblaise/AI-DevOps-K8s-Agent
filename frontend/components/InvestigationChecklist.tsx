"use client";

import { STEP_EVENTS, STEP_LABELS, StepEvent } from "@/types/investigation";

interface Props {
  completedSteps: Set<StepEvent>;
  done: boolean;
}

export function InvestigationChecklist({ completedSteps, done }: Props) {
  // The fixed step order, plus the terminal "Root Cause Found" row.
  const rows: { key: StepEvent | "done"; label: string; complete: boolean }[] = [
    ...STEP_EVENTS.map((step) => ({
      key: step,
      label: STEP_LABELS[step],
      complete: completedSteps.has(step),
    })),
    { key: "done", label: STEP_LABELS.done, complete: done },
  ];

  // The first incomplete row is "in progress".
  const activeIndex = rows.findIndex((r) => !r.complete);

  return (
    <ol className="space-y-1 rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      {rows.map((row, i) => {
        const state = row.complete
          ? "complete"
          : i === activeIndex
            ? "active"
            : "pending";
        return (
          <li key={row.key} className="flex items-center gap-3 rounded-lg px-1.5 py-1.5 text-sm">
            <span
              className={
                state === "complete"
                  ? "flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-[11px] font-bold text-white"
                  : state === "active"
                    ? "h-5 w-5 animate-pulse rounded-full border-2 border-indigo-500"
                    : "h-5 w-5 rounded-full border-2 border-gray-300 dark:border-gray-700"
              }
            >
              {state === "complete" ? "✓" : ""}
            </span>
            <span
              className={
                state === "pending"
                  ? "text-gray-400 dark:text-gray-600"
                  : state === "active"
                    ? "font-medium text-indigo-600 dark:text-indigo-400"
                    : "font-medium text-gray-800 dark:text-gray-200"
              }
            >
              {row.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
