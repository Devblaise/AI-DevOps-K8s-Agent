"use client";

import { useCallback, useRef, useState } from "react";

import { streamUrl } from "@/services/api";
import {
  InvestigationEvidence,
  STEP_EVENTS,
  StepEvent,
} from "@/types/investigation";

export type InvestigationPhase = "idle" | "streaming" | "done" | "error";

// No step takes this long unless something is wrong; guards against a hung stream.
const STREAM_TIMEOUT_MS = 90_000;

export interface UseInvestigation {
  phase: InvestigationPhase;
  /** Step events received so far (drives the live checklist). */
  completedSteps: Set<StepEvent>;
  evidence: InvestigationEvidence | null;
  error: string | null;
  start: (context: string, namespace?: string) => void;
  reset: () => void;
}

export function useInvestigation(): UseInvestigation {
  const [phase, setPhase] = useState<InvestigationPhase>("idle");
  const [completedSteps, setCompletedSteps] = useState<Set<StepEvent>>(new Set());
  const [evidence, setEvidence] = useState<InvestigationEvidence | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sourceRef = useRef<EventSource | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Tracks whether the stream already reached a terminal state, so a late native
  // EventSource "error" (which fires with no data after the server closes) doesn't
  // overwrite a successful "done". A ref avoids the stale-closure problem a state
  // value would have inside the listener.
  const settledRef = useRef(false);

  const cleanup = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    cleanup();
    settledRef.current = false;
    setPhase("idle");
    setCompletedSteps(new Set());
    setEvidence(null);
    setError(null);
  }, [cleanup]);

  const fail = useCallback(
    (message: string) => {
      if (settledRef.current) return;
      settledRef.current = true;
      cleanup();
      setError(message);
      setPhase("error");
    },
    [cleanup],
  );

  const start = useCallback(
    (context: string, namespace?: string) => {
      cleanup();
      settledRef.current = false;
      setCompletedSteps(new Set());
      setEvidence(null);
      setError(null);
      setPhase("streaming");

      const source = new EventSource(streamUrl(context, namespace));
      sourceRef.current = source;

      const armTimeout = () => {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(
          () => fail("The investigation timed out. Please try again."),
          STREAM_TIMEOUT_MS,
        );
      };
      armTimeout();

      // Tick each step off the checklist as its event arrives.
      for (const step of STEP_EVENTS) {
        source.addEventListener(step, () => {
          armTimeout();
          setCompletedSteps((prev) => new Set(prev).add(step));
        });
      }

      source.addEventListener("done", (ev) => {
        if (settledRef.current) return;
        try {
          const data = JSON.parse((ev as MessageEvent).data) as InvestigationEvidence;
          settledRef.current = true;
          setEvidence(data);
          setPhase("done");
          cleanup();
        } catch {
          fail("Could not parse the investigation result.");
        }
      });

      source.addEventListener("error", (ev) => {
        // Backend-emitted error event carries a friendly { message } payload.
        const raw = (ev as MessageEvent).data;
        if (raw) {
          try {
            const data = JSON.parse(raw) as { message?: string };
            fail(data.message || "The investigation failed.");
            return;
          } catch {
            /* fall through to generic handling */
          }
        }
        // Native EventSource error with no data (connection dropped / backend down).
        // Ignored if we've already settled, since EventSource also fires this when the
        // server closes the stream normally after "done".
        fail("Lost connection to the backend. Check that it's running, then try again.");
      });
    },
    [cleanup, fail],
  );

  return { phase, completedSteps, evidence, error, start, reset };
}
