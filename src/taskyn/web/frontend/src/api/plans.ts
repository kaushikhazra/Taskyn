import { api } from './client';
import type {
  Plan, PlanCreate, PlanUpdate, PlanListFilters,
  PlanItemEnriched, PlanItemAdd, PlanItemUpdate, PlanItemReorder,
  CarryOverRequest, CarryOverResult,
  WeeklyPlan, MonthlyPlan, PlanVsActual,
} from '@/types';

export const plansApi = {
  // -- Plan CRUD --------------------------------------------------------

  create: (data: PlanCreate) =>
    api.post<Plan>('/plans', data),

  list: (filters?: PlanListFilters) => {
    const params = new URLSearchParams();
    if (filters?.actor)     params.set('actor', filters.actor);
    if (filters?.date_from) params.set('date_from', filters.date_from);
    if (filters?.date_to)   params.set('date_to', filters.date_to);
    if (filters?.status)    params.set('status', filters.status);
    if (filters?.limit)     params.set('limit', String(filters.limit));
    if (filters?.offset)    params.set('offset', String(filters.offset));
    return api.get<Plan[]>(`/plans?${params}`);
  },

  get: (planId: string) =>
    api.get<Plan>(`/plans/${planId}`),

  /** Fetch plan by date + actor — dedicated endpoint, returns Plan or null. */
  getByDate: (date: string, actor: string) =>
    api.get<Plan | null>(`/plans/by-date?date=${date}&actor=${actor}`),

  /** Fetch all actors' plans for a date, each enriched with items. */
  forDate: (date: string) =>
    api.get<Plan[]>(`/plans/for-date?date=${date}`),

  update: (planId: string, data: PlanUpdate) =>
    api.patch<Plan>(`/plans/${planId}`, data),

  delete: (planId: string) =>
    api.delete(`/plans/${planId}`),

  // -- Plan Items -------------------------------------------------------

  addItem: (planId: string, data: PlanItemAdd) =>
    api.post<PlanItemEnriched>(`/plans/${planId}/items`, data),

  updateItem: (itemId: string, data: PlanItemUpdate) =>
    api.patch<PlanItemEnriched>(`/plans/items/${itemId}`, data),

  removeItem: (itemId: string) =>
    api.delete(`/plans/items/${itemId}`),

  reorderItem: (itemId: string, data: PlanItemReorder) =>
    api.post<Plan>(`/plans/items/${itemId}/reorder`, data),

  // -- Aggregated Views -------------------------------------------------

  weekly: (weekStart: string, actor?: string) => {
    const params = new URLSearchParams({ week_start_date: weekStart });
    if (actor) params.set('actor', actor);
    return api.get<WeeklyPlan>(`/plans/weekly?${params}`);
  },

  monthly: (year: number, month: number, actor?: string) => {
    const params = new URLSearchParams({
      year: String(year),
      month: String(month),
    });
    if (actor) params.set('actor', actor);
    return api.get<MonthlyPlan>(`/plans/monthly?${params}`);
  },

  vsActual: (date: string, actor: string) =>
    api.get<PlanVsActual>(`/plans/vs-actual?plan_date=${date}&actor=${actor}`),

  // -- Carry-Over -------------------------------------------------------

  carryOver: (planId: string, data: CarryOverRequest) =>
    api.post<CarryOverResult>(`/plans/${planId}/carry-over`, data),
};
