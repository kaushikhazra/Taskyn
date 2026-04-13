/* Taskyn TypeScript types — mirrors backend Pydantic models & MCP responses. */

// ============================================================
// Entity Type (Lifecycle Stages)
// ============================================================

export const ENTITY_TYPES = ['discovery', 'potential', 'matured', 'engaged', 'active', 'dormant'] as const;
export type EntityType = typeof ENTITY_TYPES[number];

// Fixed colors (theme-independent)
export const ENTITY_TYPE_COLORS: Record<EntityType, string> = {
  discovery: '#0077B6',  // Ocean Blue
  potential: '#FFD60A',  // Chrome Yellow
  matured: '#2A9D8F',    // Ocean Green
  engaged: '#606C38',    // Moss Green
  active: '#E63946',     // Coral Red
  dormant: '#6C757D',    // Grey
};

// ============================================================
// Companies
// ============================================================

export interface Company {
  id: string;
  name: string;
  description: string | null;
  type: EntityType;
  created_at: string;
  updated_at: string;
  stats?: CompanyStats;
}

export interface CompanyStats {
  total_projects: number;
  total_nodes: number;
  completed_nodes: number;
  completion_percentage: number;
  total_time_minutes: number;
}

export interface CompanyCreate {
  name: string;
  description?: string;
  type?: EntityType;
}

// ============================================================
// Projects
// ============================================================

export interface Project {
  id: string;
  name: string;
  company_id: string | null;
  methodology: string;
  description: string | null;
  type: EntityType;
  status: string;
  created_at: string;
  updated_at: string;
  stats?: ProjectStats;
}

export interface ProjectStats {
  total_nodes: number;
  completed_nodes: number;
  nodes_by_type: Record<string, number>;
  nodes_by_status: Record<string, number>;
  completion_percentage: number;
  time_total: number;
}

export interface ProjectCreate {
  company_id: string;
  name: string;
  methodology?: string;
  description?: string;
  type?: EntityType;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  status?: string;
  type?: EntityType;
  methodology?: string;
}

// ============================================================
// Nodes
// ============================================================

export interface Node {
  id: string;
  project_id: string;
  node_type: string;
  title: string;
  description: string | null;
  status: string;
  assignee: string | null;
  priority: string | null;
  milestone_id: string | null;
  properties: Record<string, unknown> | null;
  actual_time: number;
  blocked_reason: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  parent_id?: string | null;
  // Composite fields from pm_get_node
  edges?: Edge[];
  outgoing_edges?: Edge[];
  incoming_edges?: Edge[];
  time_entries?: TimeEntry[];
  rollup?: NodeRollup;
}

export interface NodeCreate {
  project_id: string;
  node_type: string;
  title: string;
  description?: string;
  assignee?: string;
  priority?: string;
  milestone_id?: string;
  parent_id?: string;
}

export interface NodeUpdate {
  title?: string;
  description?: string;
  status?: string;
  assignee?: string;
  priority?: string;
  milestone_id?: string;
}

export interface NodeRollup {
  total_children: number;
  completed_children: number;
  total_time_minutes: number;
  statuses: Record<string, number>;
}

// ============================================================
// Edges
// ============================================================

export interface Edge {
  id: string;
  source_id: string;
  target_id: string;
  edge_type: string;
  created_at: string;
}

export interface EdgeCreate {
  source_id: string;
  target_id: string;
  edge_type: string;
}

// ============================================================
// Milestones
// ============================================================

export interface Milestone {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  target_date: string | null;
  status: string;
  completed_at: string | null;
  created_at: string;
}

export interface MilestoneCreate {
  project_id: string;
  name: string;
  target_date?: string;
  description?: string;
}

export interface MilestoneUpdate {
  name?: string;
  description?: string;
  target_date?: string;
}

// ============================================================
// Tags
// ============================================================

export interface Tag {
  id: string;
  name: string;
  color: string | null;
}

export interface TagCreate {
  name: string;
  color?: string;
}

export interface TagUsage {
  tag_name: string;
  usage_count: number;
}

export interface TagDeleteResult {
  deleted: boolean;
  usage_count: number;
}

// ============================================================
// Time Tracking
// ============================================================

export interface TimeEntry {
  id: string;
  node_id: string;
  duration_minutes: number | null;
  notes: string | null;
  started_at: string;
  ended_at: string | null;
  actor: string | null;
  node_title?: string;
}

export interface TimeEntryCreate {
  node_id: string;
  duration_minutes: number;
  notes?: string;
}

export interface ActiveTimer {
  id: string;
  node_id: string;
  node_title?: string;
  notes: string | null;
  actor: string | null;
  started_at: string;
}

// ============================================================
// Dashboard & Reporting
// ============================================================

export interface Dashboard {
  total_companies: number;
  total_projects: number;
  total_nodes: number;
  nodes_by_status: Record<string, number>;
  recent_activity: ActivityEntry[];
}

export interface ActivityEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  node_type: string | null;
  action: string;
  old_value: string | null;
  new_value: string | null;
  actor: string;
  notes: string | null;
  created_at: string;
}

export interface SearchResult {
  entity_type: string;
  entity_id: string;
  title: string;
  snippet: string | null;
  score: number;
}

// ============================================================
// Methodology
// ============================================================

export interface MethodologyInfo {
  name: string;
  node_types: string[];
  statuses: string[];
  transitions: Record<string, string[]>;
  hierarchy: Record<string, string[]>;
}

// ============================================================
// Plans — Enums
// ============================================================

export const PLAN_STATUSES = ['active', 'completed'] as const;
export type PlanStatus = typeof PLAN_STATUSES[number];

export const PLAN_OUTCOMES = ['pending', 'completed', 'partial', 'carried_over', 'dropped'] as const;
export type PlanOutcome = typeof PLAN_OUTCOMES[number];

// ============================================================
// Plans — Core Models
// ============================================================

/** A single day's plan for one actor. */
export interface Plan {
  id: string;
  date: string;                          // "YYYY-MM-DD"
  actor: string;
  status: PlanStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
  items: PlanItemEnriched[];             // always present on get/create responses
}

/** Plan item as stored — no node enrichment. */
export interface PlanItem {
  id: string;
  plan_id: string;
  node_id: string | null;
  planned_minutes: number | null;
  display_order: number;
  outcome: PlanOutcome;
  outcome_notes: string | null;
  carried_to_plan_id: string | null;
  created_at: string;
  updated_at: string;
}

/** Plan item enriched with joined node/project data (returned by get_plan). */
export interface PlanItemEnriched extends PlanItem {
  node_title: string | null;
  node_status: string | null;
  node_type: string | null;
  project_id: string | null;
  project_name: string | null;
  estimated_minutes: number | null;
  actual_time: number | null;
  node_deleted: boolean;
}

// ============================================================
// Plans — Create / Update DTOs
// ============================================================

export interface PlanCreate {
  date: string;                          // "YYYY-MM-DD"
  actor: string;
  notes?: string;
  items?: PlanItemSeed[];
}

export interface PlanItemSeed {
  node_id: string;
  planned_minutes?: number;
  display_order?: number;                // matches backend PlanItemInline field name
}

export interface PlanUpdate {
  notes?: string;
  status?: PlanStatus;
}

export interface PlanItemAdd {
  node_id: string;
  planned_minutes?: number;
  position?: number;
}

export interface PlanItemUpdate {
  outcome?: PlanOutcome;
  outcome_notes?: string;
  planned_minutes?: number;
}

export interface PlanItemReorder {
  new_position: number;
}

// ============================================================
// Plans — Carry-Over
// ============================================================

export interface CarryOverRequest {
  target_date: string;                   // "YYYY-MM-DD"
  item_ids?: string[];                   // null = carry all eligible
}

export interface CarryOverResult {
  source_plan_id: string;
  target_plan: Plan;
  carried_count: number;
  skipped: CarryOverSkip[];
}

export interface CarryOverSkip {
  item_id: string;
  node_id: string | null;
  reason: string;
}

// ============================================================
// Plans — Weekly View
// ============================================================

export interface WeeklyPlan {
  week_start: string;                    // "YYYY-MM-DD" (Monday)
  week_end: string;                      // "YYYY-MM-DD" (Sunday)
  days: WeeklyDaySummary[];              // 7 entries (Mon–Sun), per-day summary
  summary: WeeklyPlanSummary;
}

/** Per-day summary for WeekGrid — lightweight, no full Plan/item payloads. */
export interface WeeklyDaySummary {
  date: string;                          // "YYYY-MM-DD"
  plan_id: string | null;               // null if no plan for this day
  status: PlanStatus | null;
  item_count: number;
  outcomes: Record<PlanOutcome, number>;
  planned_minutes: number;
  actual_minutes: number;
}

export interface WeeklyPlanSummary {
  total_planned_items: number;
  total_planned_minutes: number;
  outcomes: Record<PlanOutcome, number>;
  actual_minutes: number;
}

// ============================================================
// Plans — Monthly View
// ============================================================

export interface MonthlyPlan {
  year: number;
  month: number;
  days_in_month: number;
  days_with_plans: number;
  total_planned_items: number;
  total_planned_minutes: number;
  outcomes: Record<PlanOutcome, number>;
  actual_minutes: number;
  days: MonthlyDaySummary[];            // per-day breakdown for calendar grid
  per_actor: MonthlyActorSummary[];
  milestones: MonthlyMilestone[];
}

/** Per-day summary for MonthCalendarGrid — one entry per day that has a plan. */
export interface MonthlyDaySummary {
  date: string;                          // "YYYY-MM-DD"
  plan_id: string;
  status: PlanStatus;
  item_count: number;
  outcomes: Record<PlanOutcome, number>;
  planned_minutes: number;
  actual_minutes: number;
}

export interface MonthlyActorSummary {
  actor: string;
  days_with_plans: number;
  total_planned_items: number;
  total_planned_minutes: number;
  outcomes: Record<PlanOutcome, number>;
  actual_minutes: number;
}

export interface MonthlyMilestone {
  id: string;
  name: string;
  project_id: string;
  project_name: string;
  target_date: string | null;
  status: string;
}

// ============================================================
// Plans — Plan vs Actual
// ============================================================

export interface PlanVsActual {
  date: string;
  actor: string;
  planned_items: PlanVsActualItem[];
  unplanned_items: UnplannedItem[];
  summary: PlanVsActualSummary;
}

export interface PlanVsActualItem {
  node_id: string | null;
  title: string | null;
  planned_minutes: number | null;
  display_order: number;
  actual_minutes: number;
  current_status: string | null;
  is_terminal: boolean;
  delta_minutes: number | null;
  outcome: PlanOutcome;
  outcome_notes: string | null;
}

export interface UnplannedItem {
  node_id: string;
  title: string;
  actual_minutes: number;
  current_status: string;
  project_id: string;
  project_name: string;
}

export interface PlanVsActualSummary {
  total_planned_minutes: number;
  total_actual_minutes: number;
  total_unplanned_minutes: number;
  planned_item_count: number;
  completed_count: number;
  unplanned_item_count: number;
  overall_delta: number | null;
}

// ============================================================
// Plans — Filter types (for list/query params)
// ============================================================

export interface PlanListFilters {
  actor?: string;
  date_from?: string;
  date_to?: string;
  status?: PlanStatus;
  limit?: number;
  offset?: number;
}
