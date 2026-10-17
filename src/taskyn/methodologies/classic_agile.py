"""Classic Agile methodology (Epic → Story → Task)."""

from taskyn.methodologies.base import (
    BaseMethodology,
    NodeTypeDefinition,
    EdgeTypeDefinition,
)


class ClassicAgileMethodology(BaseMethodology):
    """
    Classic Agile methodology with Epics, Stories, and Tasks.

    Hierarchy:
        Epic
        └── Story
            └── Task

    Epic statuses: draft → ready → in_progress → done/cancelled
    Story statuses: backlog → ready → in_progress → done/cancelled
    Task statuses: todo → in_progress → blocked → in_review → done/cancelled
    """

    @property
    def name(self) -> str:
        return "classic_agile"

    @property
    def display_name(self) -> str:
        return "Classic Agile"

    @property
    def node_types(self) -> dict[str, NodeTypeDefinition]:
        return {
            "epic": NodeTypeDefinition(
                name="epic",
                valid_statuses=["draft", "ready", "in_progress", "done", "cancelled"],
                initial_status="draft",
                terminal_statuses={"done", "cancelled"},
                allowed_transitions={
                    "draft": ["ready", "cancelled"],
                    "ready": ["in_progress", "draft", "cancelled"],
                    "in_progress": ["done", "ready", "cancelled"],
                    "done": [],
                    "cancelled": [],
                },
                can_track_time=False,
            ),
            "story": NodeTypeDefinition(
                name="story",
                valid_statuses=["backlog", "ready", "in_progress", "done", "cancelled"],
                initial_status="backlog",
                terminal_statuses={"done", "cancelled"},
                allowed_transitions={
                    "backlog": ["ready", "cancelled"],
                    "ready": ["in_progress", "backlog", "cancelled"],
                    "in_progress": ["done", "ready", "cancelled"],
                    "done": [],
                    "cancelled": [],
                },
                optional_properties=["acceptance_criteria", "story_points"],
            ),
            "task": NodeTypeDefinition(
                name="task",
                valid_statuses=[
                    "todo",
                    "in_progress",
                    "blocked",
                    "in_review",
                    "done",
                    "cancelled",
                ],
                initial_status="todo",
                terminal_statuses={"done", "cancelled"},
                allowed_transitions={
                    "todo": ["in_progress", "cancelled"],
                    "in_progress": ["blocked", "in_review", "done", "todo", "cancelled"],
                    "blocked": ["in_progress", "cancelled"],
                    "in_review": ["done", "in_progress", "cancelled"],
                    "done": [],
                    "cancelled": [],
                },
                can_be_planned=True,
            ),
        }

    @property
    def edge_types(self) -> dict[str, EdgeTypeDefinition]:
        return {
            "parent": EdgeTypeDefinition(
                name="parent",
                source_types=["task", "story"],
                target_types=["story", "epic"],
                max_per_source=1,  # A node has exactly one parent
                allows_cycles=False,
            ),
            "sequence": EdgeTypeDefinition(
                name="sequence",
                source_types=["epic", "story", "task"],
                target_types=["epic", "story", "task"],
                max_per_source=None,
                allows_cycles=False,
            ),
            "depends_on": EdgeTypeDefinition(
                name="depends_on",
                source_types=["task", "story", "epic"],
                target_types=["task", "story", "epic"],
                allows_cycles=False,
            ),
        }

    def get_epic_type(self) -> str:
        return "epic"

    def get_story_type(self) -> str:
        return "story"

    def get_task_type(self) -> str:
        return "task"

    def get_in_progress_status(self, node_type: str) -> str:
        return "in_progress"

    def get_done_status(self, node_type: str) -> str:
        return "done"
