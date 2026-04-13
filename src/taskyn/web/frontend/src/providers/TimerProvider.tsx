import {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useActiveTimers } from '@/hooks/queries/useTimerQuery';
import { useStartTimer, useStopTimer } from '@/hooks/mutations/useTimerMutations';
import type { ActiveTimer } from '@/types';

export interface TimerContextValue {
  /** All active timers across all actors (from /timer/active). */
  activeTimers: ActiveTimer[];
  /** Map of timer id → elapsed seconds for all active timers. */
  elapsedMap: Record<string, number>;
  loading: boolean;
  start: (nodeId: string, notes?: string) => Promise<void>;
  stop: (entryId?: string) => Promise<void>;
}

export const TimerContext = createContext<TimerContextValue | null>(null);

export function TimerProvider({ children }: { children: ReactNode }) {
  // Always enabled — single-user local app, no auth gate
  const { data: activeTimers = [], isPending } = useActiveTimers({
    enabled: true,
    refetchInterval: 1_000,
  });

  const startTimer = useStartTimer();
  const stopTimer = useStopTimer();

  const [elapsedMap, setElapsedMap] = useState<Record<string, number>>({});
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const calcElapsed = useCallback((startedAt: string): number => {
    return Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  }, []);

  // Manage the elapsed tick interval for all active timers
  useEffect(() => {
    const tick = () => {
      const map: Record<string, number> = {};
      for (const t of activeTimers) {
        map[t.id] = calcElapsed(t.started_at);
      }
      setElapsedMap(map);
    };

    tick();
    intervalRef.current = setInterval(tick, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [activeTimers, calcElapsed]);

  const start = useCallback(
    async (nodeId: string, notes?: string) => {
      await startTimer.mutateAsync({ nodeId, notes });
    },
    [startTimer],
  );

  const stop = useCallback(
    async (entryId?: string) => {
      await stopTimer.mutateAsync(entryId);
    },
    [stopTimer],
  );

  const loading = isPending || startTimer.isPending || stopTimer.isPending;

  return (
    <TimerContext.Provider
      value={{ activeTimers, elapsedMap, loading, start, stop }}
    >
      {children}
    </TimerContext.Provider>
  );
}
