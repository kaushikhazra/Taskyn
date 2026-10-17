"""Base methodology class and type definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeTypeDefinition:
    """Defines a valid node type for a methodology."""

    name: str
    valid_statuses: list[str]
    initial_status: str
    terminal_statuses: set[str]
    allowed_transitions: dict[str, list[str]]
    required_properties: list[str] = field(default_factory=list)
    optional_properties: list[str] = field(default_factory=list)
    can_track_time: bool = True
    can_have_assignee: bool = True
    can_be_planned: bool = False


@dataclass
class EdgeTypeDefinition:
    """Defines a valid edge type for a methodology."""

    name: str
    source_types: list[str]
    target_types: list[str]
    max_per_source: int | None = None
    max_per_target: int | None = None
    allows_cycles: bool = False


class BaseMethodology(ABC):
    """Base class for all methodologies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the methodology."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name."""
        pass

    @property
    @abstractmethod
    def node_types(self) -> dict[str, NodeTypeDefinition]:
        """All valid node types for this methodology."""
        pass

    @property
    @abstractmethod
    def edge_types(self) -> dict[str, EdgeTypeDefinition]:
        """All valid edge types for this methodology."""
        pass

    def get_node_type(self, name: str) -> NodeTypeDefinition | None:
        """Get a node type definition by name."""
        return self.node_types.get(name)

    def get_edge_type(self, name: str) -> EdgeTypeDefinition | None:
        """Get an edge type definition by name."""
        return self.edge_types.get(name)

    def validate_node_type(self, node_type: str) -> bool:
        """Check if a node type is valid for this methodology."""
        return node_type in self.node_types

    def validate_edge_type(self, edge_type: str) -> bool:
        """Check if an edge type is valid for this methodology."""
        return edge_type in self.edge_types

    def validate_status(self, node_type: str, status: str) -> bool:
        """Check if a status is valid for the given node type."""
        nt = self.get_node_type(node_type)
        if nt is None:
            return False
        return status in nt.valid_statuses

    def validate_status_transition(
        self, node_type: str, old_status: str, new_status: str
    ) -> bool:
        """Check if a status transition is allowed.

        Any status can transition to any other valid status for the node type.
        The methodology defines *which* statuses exist, but does not gate movement
        between them — reopen, rollback, and correction flows are always permitted.
        ``allowed_transitions`` is retained on ``NodeTypeDefinition`` for
        documentation/reporting purposes only.
        """
        return self.validate_status(node_type, new_status)

    def get_initial_status(self, node_type: str) -> str | None:
        """Get the initial status for a node type."""
        nt = self.get_node_type(node_type)
        return nt.initial_status if nt else None

    def is_terminal_status(self, node_type: str, status: str) -> bool:
        """Check if a status is terminal (work is done)."""
        nt = self.get_node_type(node_type)
        if nt is None:
            return False
        return status in nt.terminal_statuses

    @property
    def valid_parent_pairs(self) -> dict[str, list[str]]:
        """Map of child_type -> allowed_parent_types for parent edges.

        Override in subclass to enforce strict hierarchy.
        Empty dict means no pair-level restriction (only source/target lists).
        """
        return {}

    def validate_edge(
        self, edge_type: str, source_type: str, target_type: str
    ) -> list[str]:
        """
        Validate an edge.

        Returns a list of validation errors (empty if valid).
        """
        errors = []
        et = self.get_edge_type(edge_type)

        if et is None:
            errors.append(f"Unknown edge type: {edge_type}")
            return errors

        if source_type not in et.source_types:
            errors.append(
                f"Node type '{source_type}' cannot be a source for edge type '{edge_type}'"
            )

        if target_type not in et.target_types:
            errors.append(
                f"Node type '{target_type}' cannot be a target for edge type '{edge_type}'"
            )

        # Pair-level validation for parent edges
        pairs = self.valid_parent_pairs
        if edge_type == "parent" and pairs:
            allowed_parents = pairs.get(source_type)
            if allowed_parents is not None and target_type not in allowed_parents:
                errors.append(
                    f"Node type '{source_type}' can only parent under "
                    f"{allowed_parents}, not '{target_type}'"
                )

        return errors

    # Helper methods for convenience API
    def get_story_type(self) -> str:
        """Return the top-level work item type (override in subclass)."""
        # Default: first node type
        return list(self.node_types.keys())[0]

    def get_task_type(self) -> str:
        """Return the child work item type (override in subclass)."""
        # Default: second node type or first if only one
        types = list(self.node_types.keys())
        return types[1] if len(types) > 1 else types[0]

    def get_in_progress_status(self, node_type: str) -> str:
        """Return the 'working on it' status for this node type."""
        return "in_progress"

    def get_done_status(self, node_type: str) -> str:
        """Return the terminal 'completed' status."""
        nt = self.get_node_type(node_type)
        if nt:
            # Return first terminal status
            return list(nt.terminal_statuses)[0]
        return "done"

    def get_blocked_status(self, node_type: str) -> str | None:
        """Return blocked status if supported, else None."""
        nt = self.get_node_type(node_type)
        if nt and "blocked" in nt.valid_statuses:
            return "blocked"
        return None
