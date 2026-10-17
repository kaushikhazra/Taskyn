"""Spec-Driven methodology v3.

Hierarchy (3 levels, 5 node types):
    spec (Level 1 — container)
    ├── requirement (Level 2 — what) → todos
    ├── design (Level 2 — how) → todos
    └── task (Level 2 — implementation grouping) → todos

Phase nodes (spec, requirement, design, task) use universal statuses:
    draft → active → done | cancelled

Todo nodes (leaf work units) support start/stop timer:
    todo → in_progress → done | cancelled

Strict gating enforces sequential phase flow:
    requirement can activate when spec is active/done
    design can activate when ALL sibling requirements are done
    task can activate when ALL sibling designs are done
    todos can start when parent phase is active/done

Time tracking is only allowed on todo nodes.
"""

from taskyn.methodologies.base import (
    BaseMethodology,
    NodeTypeDefinition,
    EdgeTypeDefinition,
)

_PHASE_TYPES = ["spec", "requirement", "design", "task"]
_ALL_TYPES = ["spec", "requirement", "design", "task", "todo"]


def _phase_node(name: str) -> NodeTypeDefinition:
    """Shared definition for phase nodes (spec, requirement, design, task)."""
    return NodeTypeDefinition(
        name=name,
        valid_statuses=["draft", "active", "done", "cancelled"],
        initial_status="draft",
        terminal_statuses={"done", "cancelled"},
        allowed_transitions={
            "draft": ["active", "cancelled"],
            "active": ["done", "cancelled"],
            "done": [],
            "cancelled": [],
        },
        can_track_time=False,
    )


class SpecDrivenMethodology(BaseMethodology):
    """Spec-Driven methodology v3 with 3-level hierarchy."""

    @property
    def name(self) -> str:
        return "spec_driven"

    @property
    def display_name(self) -> str:
        return "Spec-Driven"

    @property
    def node_types(self) -> dict[str, NodeTypeDefinition]:
        return {
            "spec": _phase_node("spec"),
            "requirement": _phase_node("requirement"),
            "design": _phase_node("design"),
            "task": _phase_node("task"),
            "todo": NodeTypeDefinition(
                name="todo",
                valid_statuses=["todo", "in_progress", "done", "cancelled"],
                initial_status="todo",
                terminal_statuses={"done", "cancelled"},
                allowed_transitions={
                    "todo": ["in_progress", "cancelled"],
                    "in_progress": ["done", "cancelled"],
                    "done": [],
                    "cancelled": [],
                },
                can_track_time=True,
                can_be_planned=True,
            ),
        }

    @property
    def edge_types(self) -> dict[str, EdgeTypeDefinition]:
        return {
            "parent": EdgeTypeDefinition(
                name="parent",
                source_types=["requirement", "design", "task", "todo"],
                target_types=["spec", "requirement", "design", "task"],
                max_per_source=1,
                allows_cycles=False,
            ),
            "sequence": EdgeTypeDefinition(
                name="sequence",
                source_types=_ALL_TYPES,
                target_types=_ALL_TYPES,
                max_per_source=None,
                allows_cycles=False,
            ),
            "depends_on": EdgeTypeDefinition(
                name="depends_on",
                source_types=_ALL_TYPES,
                target_types=_ALL_TYPES,
                allows_cycles=False,
            ),
            "blocks": EdgeTypeDefinition(
                name="blocks",
                source_types=_ALL_TYPES,
                target_types=_ALL_TYPES,
                allows_cycles=False,
            ),
        }

    @property
    def valid_parent_pairs(self) -> dict[str, list[str]]:
        return {
            "requirement": ["spec"],
            "design": ["spec"],
            "task": ["spec"],
            "todo": ["requirement", "design", "task"],
        }

    def get_story_type(self) -> str:
        return "spec"

    def get_task_type(self) -> str:
        return "todo"

    def get_in_progress_status(self, node_type: str) -> str:
        if node_type == "todo":
            return "in_progress"
        return "active"

    def get_done_status(self, node_type: str) -> str:
        return "done"
