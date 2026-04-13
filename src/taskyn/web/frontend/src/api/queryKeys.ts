/**
 * Centralized query key factory for TanStack Query.
 *
 * Invalidating a parent key (e.g. `queryKeys.nodes.all()`) automatically
 * invalidates all child keys (lists, details, ancestors, etc.) because
 * TanStack Query matches by prefix.
 */

// TODO: PlanListFilters will be provided by the types module (parallel worker)
import type { PlanListFilters } from '@/types';

export const queryKeys = {
  companies: {
    all: () => ['companies'] as const,
    list: (filters?: { includeStats?: boolean }) =>
      [...queryKeys.companies.all(), 'list', filters] as const,
    detail: (id: string) =>
      [...queryKeys.companies.all(), 'detail', id] as const,
    stats: (id: string) =>
      [...queryKeys.companies.all(), 'stats', id] as const,
  },

  projects: {
    all: () => ['projects'] as const,
    list: (filters?: { company_id?: string; status?: string; include_stats?: boolean }) =>
      [...queryKeys.projects.all(), 'list', filters] as const,
    detail: (id: string) =>
      [...queryKeys.projects.all(), 'detail', id] as const,
    stats: (id: string) =>
      [...queryKeys.projects.all(), 'stats', id] as const,
    methodology: (id: string) =>
      [...queryKeys.projects.all(), 'methodology', id] as const,
  },

  nodes: {
    all: () => ['nodes'] as const,
    list: (filters?: { project_id?: string; node_type?: string; status?: string; assignee?: string }) =>
      [...queryKeys.nodes.all(), 'list', filters] as const,
    detail: (id: string) =>
      [...queryKeys.nodes.all(), 'detail', id] as const,
    ancestors: (id: string, edgeType?: string) =>
      [...queryKeys.nodes.all(), 'ancestors', id, edgeType] as const,
    descendants: (id: string, edgeType?: string) =>
      [...queryKeys.nodes.all(), 'descendants', id, edgeType] as const,
    rollup: (id: string) =>
      [...queryKeys.nodes.all(), 'rollup', id] as const,
  },

  edges: {
    all: () => ['edges'] as const,
    list: (filters?: { project_id?: string; source_id?: string; target_id?: string; edge_type?: string }) =>
      [...queryKeys.edges.all(), 'list', filters] as const,
  },

  milestones: {
    all: () => ['milestones'] as const,
    list: (projectId: string, status?: string) =>
      [...queryKeys.milestones.all(), 'list', projectId, status] as const,
    detail: (id: string) =>
      [...queryKeys.milestones.all(), 'detail', id] as const,
  },

  dashboard: {
    all: () => ['dashboard'] as const,
  },

  activity: {
    all: () => ['activity'] as const,
    list: (filters?: { limit?: number; entity_type?: string; entity_id?: string }) =>
      [...queryKeys.activity.all(), 'list', filters] as const,
  },

  timer: {
    all: () => ['timer'] as const,
    current: () => [...queryKeys.timer.all(), 'current'] as const,
    active: () => [...queryKeys.timer.all(), 'active'] as const,
    list: (projectId?: string) =>
      [...queryKeys.timer.all(), 'list', projectId] as const,
    entry: (id: string) =>
      [...queryKeys.timer.all(), 'entry', id] as const,
  },

  tags: {
    all: () => ['tags'] as const,
    list: () => [...queryKeys.tags.all(), 'list'] as const,
    usage: (name: string) =>
      [...queryKeys.tags.all(), 'usage', name] as const,
  },

  plans: {
    all: () => ['plans'] as const,

    list: (filters?: PlanListFilters) =>
      [...queryKeys.plans.all(), 'list', filters] as const,

    /** Primary daily lookup — keyed by date + actor. */
    byDate: (date: string, actor: string) =>
      [...queryKeys.plans.all(), 'byDate', date, actor] as const,

    detail: (planId: string) =>
      [...queryKeys.plans.all(), 'detail', planId] as const,

    weekly: (weekStart: string, actor?: string) =>
      [...queryKeys.plans.all(), 'weekly', weekStart, actor] as const,

    monthly: (year: number, month: number, actor?: string) =>
      [...queryKeys.plans.all(), 'monthly', year, month, actor] as const,

    vsActual: (date: string, actor: string) =>
      [...queryKeys.plans.all(), 'vsActual', date, actor] as const,
  },

  search: {
    all: () => ['search'] as const,
    results: (query: string, filters?: { entity_type?: string; project_id?: string; limit?: number }) =>
      [...queryKeys.search.all(), query, filters] as const,
  },
} as const;
