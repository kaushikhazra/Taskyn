"""Extended Spec methodology.

Models the full spec-enhanced development lifecycle:

    research  (top-level — freestanding investigation)
    plan      (top-level — container for specs)
    └── spec  (container for phase nodes)
        ├── requirement  (what phase)
        ├── design       (how phase)
        ├── dryrun       (review phase — appears twice in the sequence chain)
        ├── implement    (build phase)
        └── (all of the above) → todo  (atomic work unit)

Canonical sequence chain under a spec (connected by sequence edges):
    requirement → design → dryrun → implement → dryrun

All node types share the same status set:
    draft → active → done | cancelled

Any-to-any status transitions are allowed (no gating).
Time tracking and planning are restricted to todo nodes only.
"""

from taskyn.methodologies.base import (
    BaseMethodology,
    EdgeTypeDefinition,
    NodeTypeDefinition,
)

_PHASE_TYPES = ["research", "plan", "spec", "requirement", "design", "dryrun", "implement"]
_ALL_TYPES = [*_PHASE_TYPES, "todo"]

_STANDARD_STATUSES = ["draft", "active", "done", "cancelled"]
_STANDARD_INITIAL = "draft"
_STANDARD_TERMINALS = {"done", "cancelled"}
_STANDARD_TRANSITIONS = {
    "draft": ["active", "done", "cancelled"],
    "active": ["draft", "done", "cancelled"],
    "done": ["draft", "active", "cancelled"],
    "cancelled": ["draft", "active", "done"],
}


def _phase_node(name: str) -> NodeTypeDefinition:
    """Shared definition for all phase nodes (not todo)."""
    return NodeTypeDefinition(
        name=name,
        valid_statuses=_STANDARD_STATUSES,
        initial_status=_STANDARD_INITIAL,
        terminal_statuses=_STANDARD_TERMINALS,
        allowed_transitions=_STANDARD_TRANSITIONS,
        can_track_time=False,
        can_be_planned=False,
    )


class ExtendedSpecMethodology(BaseMethodology):
    """Extended Spec methodology with 8 node types and full lifecycle support."""

    @property
    def name(self) -> str:
        return "extended_spec"

    @property
    def display_name(self) -> str:
        return "Extended Spec"

    @property
    def node_types(self) -> dict[str, NodeTypeDefinition]:
        return {
            "research": _phase_node("research"),
            "plan": _phase_node("plan"),
            "spec": _phase_node("spec"),
            "requirement": _phase_node("requirement"),
            "design": _phase_node("design"),
            "dryrun": _phase_node("dryrun"),
            "implement": _phase_node("implement"),
            "todo": NodeTypeDefinition(
                name="todo",
                valid_statuses=_STANDARD_STATUSES,
                initial_status=_STANDARD_INITIAL,
                terminal_statuses=_STANDARD_TERMINALS,
                allowed_transitions=_STANDARD_TRANSITIONS,
                can_track_time=True,
                can_be_planned=True,
            ),
        }

    @property
    def edge_types(self) -> dict[str, EdgeTypeDefinition]:
        return {
            "parent": EdgeTypeDefinition(
                name="parent",
                source_types=["spec", "requirement", "design", "dryrun", "implement", "todo"],
                target_types=["plan", "spec", "requirement", "design", "dryrun", "implement", "research"],
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
            "spec": ["plan"],
            "requirement": ["spec"],
            "design": ["spec"],
            "dryrun": ["spec"],
            "implement": ["spec"],
            "todo": ["requirement", "design", "dryrun", "implement", "research", "plan"],
        }

    def get_story_type(self) -> str:
        return "spec"

    def get_task_type(self) -> str:
        return "todo"

    def get_in_progress_status(self, node_type: str) -> str:
        return "active"

    def get_done_status(self, node_type: str) -> str:
        return "done"

    def get_blocked_status(self, node_type: str) -> str | None:
        return None
