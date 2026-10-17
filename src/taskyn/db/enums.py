"""Enumerations for Taskyn entities."""

from enum import Enum


class EntityType(str, Enum):
    """Lifecycle stage for companies and projects.

    Values map to fixed colors in the UI:
    - DISCOVERY: Ocean Blue (#0077B6)
    - POTENTIAL: Chrome Yellow (#FFD60A)
    - MATURED: Ocean Green (#2A9D8F)
    - ENGAGED: Moss Green (#606C38)
    - ACTIVE: Coral Red (#E63946)
    - DORMANT: Grey (#6C757D)
    """

    DISCOVERY = "discovery"
    POTENTIAL = "potential"
    MATURED = "matured"
    ENGAGED = "engaged"
    ACTIVE = "active"
    DORMANT = "dormant"


class Methodology(str, Enum):
    """Project management methodology.

    Defines the valid node types, statuses, and transitions for a project.
    """

    CLASSIC_AGILE = "classic_agile"
    SPEC_DRIVEN = "spec_driven"
    LEARNING = "learning"
    EXTENDED_SPEC = "extended_spec"


class PlanStatus(str, Enum):
    """Plan lifecycle status."""

    ACTIVE = "active"
    COMPLETED = "completed"


class PlanOutcome(str, Enum):
    """Outcome of a planned item at day's end.

    - PENDING: not yet resolved (default)
    - COMPLETED: node reached a terminal status
    - PARTIAL: work happened but node isn't finished
    - CARRIED_OVER: moved to a future plan (linked via carried_to_plan_id)
    - DROPPED: intentionally removed without carrying over
    """

    PENDING = "pending"
    COMPLETED = "completed"
    PARTIAL = "partial"
    CARRIED_OVER = "carried_over"
    DROPPED = "dropped"
