"""Learning methodology (Subject → Topic → Activity).

Hierarchy (3 levels, 3 node types):
    subject (Level 1 — domain container)
    └── topic (Level 2 — learning item with phase-based statuses)
        └── activity (Level 3 — leaf work unit, tracks time)

Subject statuses: planned → active → completed | archived
Topic statuses: planned → researching → practicing → documenting → completed | archived
Activity statuses: todo → in_progress → done | cancelled

Phases (researching/practicing/documenting) are advisory, not gated.
Learners can skip, revisit, or jump between phases freely.
"""

from taskyn.methodologies.base import (
    BaseMethodology,
    EdgeTypeDefinition,
    NodeTypeDefinition,
)

_ALL_TYPES = ["subject", "topic", "activity"]


class LearningMethodology(BaseMethodology):
    """Learning methodology with flexible phase-based workflow."""

    @property
    def name(self) -> str:
        return "learning"

    @property
    def display_name(self) -> str:
        return "Learning"

    @property
    def node_types(self) -> dict[str, NodeTypeDefinition]:
        return {
            "subject": NodeTypeDefinition(
                name="subject",
                valid_statuses=["planned", "active", "completed", "archived"],
                initial_status="planned",
                terminal_statuses={"completed", "archived"},
                allowed_transitions={
                    "planned": ["active", "archived"],
                    "active": ["completed", "archived"],
                    "completed": ["archived"],
                    "archived": [],
                },
                can_track_time=False,
                can_have_assignee=True,
            ),
            "topic": NodeTypeDefinition(
                name="topic",
                valid_statuses=[
                    "planned",
                    "researching",
                    "practicing",
                    "documenting",
                    "completed",
                    "archived",
                ],
                initial_status="planned",
                terminal_statuses={"completed", "archived"},
                allowed_transitions={
                    "planned": ["researching", "practicing", "documenting", "completed", "archived"],
                    "researching": ["practicing", "documenting", "completed", "archived"],
                    "practicing": ["researching", "documenting", "completed", "archived"],
                    "documenting": ["researching", "practicing", "completed", "archived"],
                    "completed": ["archived"],
                    "archived": [],
                },
                can_track_time=False,
                can_have_assignee=True,
            ),
            "activity": NodeTypeDefinition(
                name="activity",
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
                can_have_assignee=True,
                can_be_planned=True,
            ),
        }

    @property
    def edge_types(self) -> dict[str, EdgeTypeDefinition]:
        return {
            "parent": EdgeTypeDefinition(
                name="parent",
                source_types=["topic", "activity"],
                target_types=["subject", "topic"],
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
            "relates_to": EdgeTypeDefinition(
                name="relates_to",
                source_types=_ALL_TYPES,
                target_types=_ALL_TYPES,
                allows_cycles=True,
            ),
        }

    @property
    def valid_parent_pairs(self) -> dict[str, list[str]]:
        return {
            "topic": ["subject"],
            "activity": ["topic"],
        }

    def get_story_type(self) -> str:
        return "topic"

    def get_task_type(self) -> str:
        return "activity"

    def get_in_progress_status(self, node_type: str) -> str:
        if node_type == "activity":
            return "in_progress"
        if node_type == "topic":
            return "researching"
        return "active"

    def get_done_status(self, node_type: str) -> str:
        if node_type == "activity":
            return "done"
        return "completed"

    def get_blocked_status(self, node_type: str) -> str | None:
        return None
