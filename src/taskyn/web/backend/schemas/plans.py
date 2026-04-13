"""Plan request schemas."""

from datetime import date

from pydantic import BaseModel, Field


class PlanItemInline(BaseModel):
    """Inline plan item for plan creation."""
    node_id: str = Field(max_length=64)
    planned_minutes: int | None = Field(default=None, ge=0)
    display_order: int | None = Field(default=None, ge=1)


class PlanCreate(BaseModel):
    """Create plan request."""
    date: date
    actor: str = Field(max_length=100)
    notes: str | None = Field(default=None, max_length=5000)
    items: list[PlanItemInline] | None = None


class PlanUpdate(BaseModel):
    """Update plan request."""
    notes: str | None = None
    status: str | None = Field(default=None, max_length=32)


class PlanItemAdd(BaseModel):
    """Add item to plan request."""
    node_id: str = Field(max_length=64)
    planned_minutes: int | None = Field(default=None, ge=0)
    position: int | None = Field(default=None, ge=1)


class PlanItemUpdate(BaseModel):
    """Update plan item request."""
    planned_minutes: int | None = None
    outcome: str | None = Field(default=None, max_length=32)
    outcome_notes: str | None = Field(default=None, max_length=5000)


class PlanItemReorder(BaseModel):
    """Reorder plan item request."""
    new_position: int = Field(ge=1)


class CarryOverRequest(BaseModel):
    """Carry over pending items to another date."""
    target_date: date
    item_ids: list[str] | None = None
