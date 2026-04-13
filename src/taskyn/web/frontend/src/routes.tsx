import { lazy, Suspense } from 'react';
import { type RouteObject } from 'react-router-dom';
import { AppShell } from '@/components/templates/AppShell';
import { ErrorBoundary } from '@/components/organisms';

/* ============================================================
   Lazy-loaded pages
   ============================================================ */
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })));
const CompaniesPage = lazy(() => import('@/pages/CompaniesPage').then((m) => ({ default: m.CompaniesPage })));
const ProjectsPage = lazy(() => import('@/pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage })));
const ProjectDetailPage = lazy(() => import('@/pages/ProjectDetailPage').then((m) => ({ default: m.ProjectDetailPage })));
const NodeDetailPage = lazy(() => import('@/pages/NodeDetailPage').then((m) => ({ default: m.NodeDetailPage })));
const KanbanPage = lazy(() => import('@/pages/KanbanPage').then((m) => ({ default: m.KanbanPage })));
const PlannerPage = lazy(() => import('@/pages/PlannerPage').then((m) => ({ default: m.PlannerPage })));
const TrackerPage = lazy(() => import('@/pages/TrackerPage').then((m) => ({ default: m.TrackerPage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })));

/* ============================================================
   Loading fallback
   ============================================================ */
function LoadingFallback() {
  return (
    <div className="auth-layout">
      <p className="text-secondary">Loading...</p>
    </div>
  );
}

/* ============================================================
   Shell wrapper — wraps all app pages in AppShell + ErrorBoundary
   ============================================================ */
function ShellPage({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <ErrorBoundary>
        <Suspense fallback={<LoadingFallback />}>{children}</Suspense>
      </ErrorBoundary>
    </AppShell>
  );
}

/* ============================================================
   Route definitions
   ============================================================ */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <ShellPage><DashboardPage /></ShellPage>,
  },
  {
    path: '/dashboard',
    element: <ShellPage><DashboardPage /></ShellPage>,
  },
  {
    path: '/companies',
    element: <ShellPage><CompaniesPage /></ShellPage>,
  },
  {
    path: '/projects',
    element: <ShellPage><ProjectsPage /></ShellPage>,
  },
  {
    path: '/projects/:projectId',
    element: <ShellPage><ProjectDetailPage /></ShellPage>,
  },
  {
    path: '/nodes/:nodeId',
    element: <ShellPage><NodeDetailPage /></ShellPage>,
  },
  {
    path: '/kanban',
    element: <ShellPage><KanbanPage /></ShellPage>,
  },
  {
    path: '/kanban/:projectId',
    element: <ShellPage><KanbanPage /></ShellPage>,
  },
  {
    path: '/planner',
    element: <ShellPage><PlannerPage /></ShellPage>,
  },
  {
    path: '/planner/:projectId',
    element: <ShellPage><PlannerPage /></ShellPage>,
  },
  {
    path: '/tracker',
    element: <ShellPage><TrackerPage /></ShellPage>,
  },
  {
    path: '/settings',
    element: <ShellPage><SettingsPage /></ShellPage>,
  },
  {
    path: '*',
    element: (
      <Suspense fallback={<LoadingFallback />}>
        <NotFoundPage />
      </Suspense>
    ),
  },
];
