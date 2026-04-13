import { useQuery } from '@tanstack/react-query';
// TODO: plansApi will be provided by the API client module (parallel worker)
import { plansApi } from '@/api/plans';
import { queryKeys } from '@/api/queryKeys';
import type { PlanListFilters } from '@/types';

interface QueryOptions {
  refetchInterval?: number | false;
}

/** Fetch a single day's plan by date + actor (primary day-view hook). */
export function usePlan(date: string, actor: string, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.plans.byDate(date, actor),
    queryFn: () => plansApi.getByDate(date, actor),
    enabled: !!date && !!actor,
    refetchInterval: options?.refetchInterval ?? false,   // plans are user-driven, no polling
  });
}

/** Fetch a plan by ID (used after carry-over to show target plan). */
export function usePlanById(planId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.plans.detail(planId!),
    queryFn: () => plansApi.get(planId!),
    enabled: !!planId,
  });
}

/** List plans with optional filters (plan history / date range). */
export function usePlans(filters?: PlanListFilters) {
  return useQuery({
    queryKey: queryKeys.plans.list(filters),
    queryFn: () => plansApi.list(filters),
  });
}

/** Weekly aggregate view — 7-day overview for one actor. */
export function useWeeklyPlan(weekStart: string, actor?: string, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.plans.weekly(weekStart, actor),
    queryFn: () => plansApi.weekly(weekStart, actor),
    enabled: !!weekStart,
    refetchInterval: options?.refetchInterval ?? false,
  });
}

/** Monthly aggregate view — calendar overview for one actor. */
export function useMonthlyPlan(year: number, month: number, actor?: string, options?: QueryOptions) {
  return useQuery({
    queryKey: queryKeys.plans.monthly(year, month, actor),
    queryFn: () => plansApi.monthly(year, month, actor),
    enabled: !!year && !!month,
    refetchInterval: options?.refetchInterval ?? false,
  });
}

/** Plan vs actual comparison for one day. */
export function usePlanVsActual(date: string, actor: string) {
  return useQuery({
    queryKey: queryKeys.plans.vsActual(date, actor),
    queryFn: () => plansApi.vsActual(date, actor),
    enabled: !!date && !!actor,
  });
}
