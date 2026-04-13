import { useState, useMemo } from 'react';
import { Modal } from '@/components/organisms/Modal';
import { NodePickerRow } from '@/components/molecules/NodePickerRow';
import { useNodes } from '@/hooks/queries/useNodes';
import { useProjects } from '@/hooks/queries/useProjects';
import { useAddPlanItem } from '@/hooks/mutations/usePlanMutations';
import { METHODOLOGY_HIERARCHY } from '@/config/methodology-ui';
import type { Node, Project } from '@/types';

interface NodePickerModalProps {
  open: boolean;
  onClose: () => void;
  planId: string;
}

/**
 * Plannable filtering (F-04): excludes node types that act as containers
 * (i.e., they have children in the methodology hierarchy). Only leaf node
 * types are plannable — you plan tasks/todos/activities, not epics/specs.
 */
function getPlannableTypes(methodology: string): Set<string> | null {
  const hierarchy = METHODOLOGY_HIERARCHY[methodology];
  if (!hierarchy) return null; // unknown methodology — allow all
  // Parent types are the keys; plannable types are those NOT in the keys
  const parentTypes = new Set(Object.keys(hierarchy));
  return parentTypes; // we'll invert this in the filter
}

export function NodePickerModal({ open, onClose, planId }: NodePickerModalProps) {
  const [search, setSearch] = useState('');
  const [projectFilter, setProjectFilter] = useState('');

  // Fetch nodes with active-ish statuses
  const { data: allNodes = [], isLoading: nodesLoading } = useNodes(
    { status: 'backlog' },
    { refetchInterval: false },
  );
  const { data: readyNodes = [] } = useNodes(
    { status: 'ready' },
    { refetchInterval: false },
  );
  const { data: inProgressNodes = [] } = useNodes(
    { status: 'in_progress' },
    { refetchInterval: false },
  );

  const { data: projects = [] } = useProjects(undefined, { refetchInterval: false });

  const addItem = useAddPlanItem();

  // Merge all status results, deduplicate by id
  const nodes = useMemo(() => {
    const map = new Map<string, Node>();
    [...allNodes, ...readyNodes, ...inProgressNodes].forEach((n) => map.set(n.id, n));
    return Array.from(map.values());
  }, [allNodes, readyNodes, inProgressNodes]);

  // Build project map for display + methodology lookup
  const projectMap = useMemo(
    () => new Map<string, Project>(projects.map((p) => [p.id, p])),
    [projects],
  );

  // Client-side plannable filtering: exclude container node types per methodology
  const filteredNodes = useMemo(() => {
    let result = nodes;

    // Project filter
    if (projectFilter) {
      result = result.filter((n) => n.project_id === projectFilter);
    }

    // Plannable filter: exclude parent-only types per project methodology
    result = result.filter((n) => {
      const project = projectMap.get(n.project_id);
      if (!project) return true; // no project info — allow
      const parentTypes = getPlannableTypes(project.methodology);
      if (!parentTypes) return true; // unknown methodology — allow
      return !parentTypes.has(n.node_type); // exclude container types
    });

    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((n) => n.title.toLowerCase().includes(q));
    }

    return result;
  }, [nodes, projectFilter, projectMap, search]);

  // Unique projects from the node set for dropdown
  const nodeProjects = useMemo(() => {
    const ids = new Set(nodes.map((n) => n.project_id));
    return projects.filter((p) => ids.has(p.id));
  }, [nodes, projects]);

  const handleAdd = (nodeId: string, plannedMinutes?: number) => {
    addItem.mutate({
      planId,
      data: { node_id: nodeId, planned_minutes: plannedMinutes },
    });
  };

  return (
    <Modal open={open} onClose={onClose} title="Add Item to Plan">
      <div className="node-picker">
        <div className="node-picker__filters">
          <input
            className="form-input node-picker__search"
            type="text"
            placeholder="Search nodes by title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
          <select
            className="form-select node-picker__project-filter"
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
          >
            <option value="">All projects</option>
            {nodeProjects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="node-picker__list">
          {nodesLoading ? (
            <div className="node-picker__empty">Loading nodes...</div>
          ) : filteredNodes.length === 0 ? (
            <div className="node-picker__empty">No plannable nodes found</div>
          ) : (
            filteredNodes.map((node) => {
              const project = projectMap.get(node.project_id);
              return (
                <NodePickerRow
                  key={node.id}
                  node={node}
                  methodology={project?.methodology ?? 'classic_agile'}
                  onAdd={handleAdd}
                  disabled={addItem.isPending}
                />
              );
            })
          )}
        </div>
      </div>
    </Modal>
  );
}
