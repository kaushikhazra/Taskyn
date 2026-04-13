"""Planning core module — daily plans, horizon views, plan vs actual, and carry-over."""

import calendar
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4

from taskyn.db.connection import execute, fetchone, fetchall, commit, serialized
from taskyn.db.models import Plan, PlanItem
from taskyn.db.enums import PlanStatus, PlanOutcome
from taskyn.core.activity import log_activity
from taskyn.exceptions import NotFoundError, ValidationError


# Sentinel for distinguishing "not provided" from "set to None"
UNSET = object()


# ---------------------------------------------------------------------------
# Internal time helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    """Get current UTC time."""
    return datetime.now(timezone.utc)


def _today() -> date:
    """Get current UTC date."""
    return _now().date()


def _parse_date(value) -> date:
    """Parse a date from various SQLite return types (date, datetime, str)."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Handle both "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS" forms
        return date.fromisoformat(value[:10])
    return _today()


def _parse_datetime(value) -> datetime:
    """Parse a datetime from SQLite (datetime, str, or fall back to _now)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return _now()


# ---------------------------------------------------------------------------
# Row mappers
# ---------------------------------------------------------------------------


def _row_to_plan(row) -> Plan:
    """Convert a database row to a Plan model."""
    return Plan(
        id=row["id"],
        date=_parse_date(row["date"]),
        actor=row["actor"],
        status=row["status"],
        notes=row["notes"],
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
    )


def _row_to_plan_item(row) -> PlanItem:
    """Convert a database row to a PlanItem model."""
    return PlanItem(
        id=row["id"],
        plan_id=row["plan_id"],
        node_id=row["node_id"],
        planned_minutes=row["planned_minutes"],
        display_order=row["display_order"],
        outcome=row["outcome"],
        outcome_notes=row["outcome_notes"],
        carried_to_plan_id=row["carried_to_plan_id"],
        created_at=_parse_datetime(row["created_at"]),
        updated_at=_parse_datetime(row["updated_at"]),
    )


# ---------------------------------------------------------------------------
# Display-order helpers
# ---------------------------------------------------------------------------


def _get_max_display_order(plan_id: str) -> int:
    """Return the current maximum display_order in a plan (0 when plan is empty)."""
    row = fetchone(
        "SELECT COALESCE(MAX(display_order), 0) AS max_order "
        "FROM plan_items WHERE plan_id = ?",
        (plan_id,),
    )
    return row["max_order"] if row else 0


def _shift_items_down(plan_id: str, from_position: int) -> None:
    """Shift display_order of all items at or below from_position down by 1."""
    execute(
        "UPDATE plan_items "
        "SET display_order = display_order + 1, updated_at = ? "
        "WHERE plan_id = ? AND display_order >= ?",
        (_now(), plan_id, from_position),
    )


def _recompact_display_order(plan_id: str) -> None:
    """Renumber display_order 1..N in ascending order, removing any gaps."""
    rows = fetchall(
        "SELECT id FROM plan_items WHERE plan_id = ? ORDER BY display_order ASC",
        (plan_id,),
    )
    now = _now()
    for idx, row in enumerate(rows, start=1):
        execute(
            "UPDATE plan_items SET display_order = ?, updated_at = ? WHERE id = ?",
            (idx, now, row["id"]),
        )


# ---------------------------------------------------------------------------
# Plannable validation
# ---------------------------------------------------------------------------


def _validate_node_plannable(node_id: str) -> None:
    """Check that a node's type is plannable in its project's methodology.

    Uses lazy imports to avoid circular dependencies with the graph layer.

    Raises:
        NotFoundError: If the node does not exist.
        ValidationError: If the node's type has can_be_planned=False.
    """
    from taskyn.graph.nodes import get_node
    from taskyn.core.project import get_project
    from taskyn.methodologies import get_methodology

    node = get_node(node_id)
    if node is None:
        raise NotFoundError("node", node_id)

    project = get_project(node.project_id)
    if project is None:
        return  # Cannot validate without project context — allow silently

    methodology = get_methodology(project.methodology)
    if methodology is None:
        return  # Cannot validate without methodology — allow silently

    node_type_def = methodology.get_node_type(node.node_type)
    if node_type_def is not None and not node_type_def.can_be_planned:
        raise ValidationError(
            f"Node type '{node.node_type}' is not plannable "
            f"in the {methodology.name} methodology"
        )


# ---------------------------------------------------------------------------
# Plan CRUD
# ---------------------------------------------------------------------------


def create_plan(
    plan_date: date,
    actor: str,
    notes: str | None = None,
    items: list[dict] | None = None,
) -> dict:
    """Create a daily plan for a specific date and actor.

    Args:
        plan_date: The date this plan covers.
        actor: Who this plan is for (free-form string).
        notes: Optional freetext notes for the day.
        items: Optional inline items — list of dicts with keys:
               ``node_id`` (required), ``planned_minutes`` (optional),
               ``display_order`` (optional; inferred from list position if omitted).

    Returns:
        Dict with plan fields and enriched items list.

    Raises:
        ValidationError: If a plan already exists for (date, actor), or if any
                         inline item's node type is not plannable.

    Activity logging:
        Logs exactly one ``plan_created`` activity entry for the plan regardless
        of how many inline items are provided.  Subsequent ``add_plan_item``
        calls log individual ``added`` entries per item as normal.
    """
    # Pre-validate all inline items before touching the database
    if items:
        node_ids_seen: set[str] = set()
        for item in items:
            nid = item["node_id"]
            if nid in node_ids_seen:
                raise ValidationError(f"Duplicate node_id '{nid}' in items list")
            node_ids_seen.add(nid)
            _validate_node_plannable(nid)
            pm = item.get("planned_minutes")
            if pm is not None and pm < 0:
                raise ValidationError("planned_minutes must be >= 0")
            order = item.get("display_order")
            if order is not None and order < 1:
                raise ValidationError("display_order must be >= 1")

    plan_id = uuid4().hex
    now = _now()

    with serialized():
        try:
            execute(
                """
                INSERT INTO plans (id, date, actor, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (plan_id, plan_date.isoformat(), actor, PlanStatus.ACTIVE,
                 notes, now, now),
            )
        except Exception as exc:
            if "UNIQUE constraint" in str(exc):
                raise ValidationError(
                    f"A plan already exists for actor '{actor}' on {plan_date}"
                ) from exc
            raise

        if items:
            for idx, item in enumerate(items, start=1):
                item_id = uuid4().hex
                order = item.get("display_order", idx)
                minutes = item.get("planned_minutes")
                execute(
                    """
                    INSERT INTO plan_items
                        (id, plan_id, node_id, planned_minutes, display_order,
                         outcome, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item_id, plan_id, item["node_id"], minutes, order,
                     PlanOutcome.PENDING, now, now),
                )

        log_activity(
            entity_type="plan",
            entity_id=plan_id,
            action="plan_created",
            actor=actor,
        )

        commit()

    return get_plan(plan_id=plan_id)


def get_plan(
    plan_id: str | None = None,
    plan_date: date | None = None,
    actor: str | None = None,
) -> dict | None:
    """Retrieve a plan with all its items enriched with node data.

    Lookup priority:
        1. ``plan_id`` — direct lookup by primary key
        2. ``(plan_date, actor)`` — unique pair lookup
        3. ``(plan_date, any)`` — first plan on that date when actor omitted
        4. ``(today, actor)`` — convenience default when only actor provided

    Returns:
        Dict with plan fields plus an ``items`` list.  Each item is enriched
        with ``node_title``, ``node_status``, ``node_type``, ``project_id``,
        ``project_name``, ``estimated_minutes``, ``actual_time``, and
        ``node_deleted`` (bool).  Items are ordered by ``display_order ASC``.
        Returns ``None`` when no plan matches the query (not an error).
        Items whose referenced node was deleted have ``node_deleted=True``
        and all node fields set to ``None``.
    """
    if plan_id is not None:
        plan_row = fetchone("SELECT * FROM plans WHERE id = ?", (plan_id,))
    elif plan_date is not None and actor is not None:
        plan_row = fetchone(
            "SELECT * FROM plans WHERE date = ? AND actor = ?",
            (plan_date.isoformat(), actor),
        )
    elif plan_date is not None:
        plan_row = fetchone(
            "SELECT * FROM plans WHERE date = ?",
            (plan_date.isoformat(),),
        )
    elif actor is not None:
        plan_row = fetchone(
            "SELECT * FROM plans WHERE date = ? AND actor = ?",
            (_today().isoformat(), actor),
        )
    else:
        return None

    if plan_row is None:
        return None

    plan = _row_to_plan(plan_row)

    # Fetch items with LEFT JOIN to nodes + projects for enrichment
    item_rows = fetchall(
        """
        SELECT
            pi.id, pi.plan_id, pi.node_id, pi.planned_minutes, pi.display_order,
            pi.outcome, pi.outcome_notes, pi.carried_to_plan_id,
            pi.created_at, pi.updated_at,
            n.title             AS node_title,
            n.status            AS node_status,
            n.node_type         AS node_type,
            n.project_id        AS project_id,
            n.estimated_minutes AS estimated_minutes,
            n.actual_time       AS actual_time,
            p.name              AS project_name
        FROM plan_items pi
        LEFT JOIN nodes n ON pi.node_id = n.id
        LEFT JOIN projects p ON n.project_id = p.id
        WHERE pi.plan_id = ?
        ORDER BY pi.display_order ASC
        """,
        (plan.id,),
    )

    items = []
    for row in item_rows:
        item = _row_to_plan_item(row)
        item_dict = item.model_dump()
        if item.node_id is None:
            # Node was deleted — ON DELETE SET NULL left node_id as NULL
            item_dict["node_deleted"] = True
            item_dict["node_title"] = None
            item_dict["node_status"] = None
            item_dict["node_type"] = None
            item_dict["project_id"] = None
            item_dict["project_name"] = None
            item_dict["estimated_minutes"] = None
            item_dict["actual_time"] = None
        else:
            item_dict["node_deleted"] = False
            item_dict["node_title"] = row["node_title"]
            item_dict["node_status"] = row["node_status"]
            item_dict["node_type"] = row["node_type"]
            item_dict["project_id"] = row["project_id"]
            item_dict["project_name"] = row["project_name"]
            item_dict["estimated_minutes"] = row["estimated_minutes"]
            item_dict["actual_time"] = row["actual_time"]
        items.append(item_dict)

    result = plan.model_dump()
    result["items"] = items
    return result


def update_plan(
    plan_id: str,
    notes=UNSET,
    status=UNSET,
    actor: str | None = None,
) -> dict:
    """Update plan metadata.

    UNSET sentinel convention: pass ``UNSET`` (the default) to leave a field
    unchanged; pass ``None`` to clear a nullable field.

    Args:
        plan_id: Plan to update.
        notes: New notes (``None`` clears, ``UNSET`` leaves unchanged).
        status: New status.  When setting to ``"completed"``, every item must
                have a non-pending outcome — raises ``ValidationError`` listing
                the blocking item IDs if any are still pending.
        actor: Actor performing the update (for activity log).

    Returns:
        Updated plan dict (same shape as ``get_plan``).

    Raises:
        NotFoundError: If the plan is not found.
        ValidationError: If completing a plan that still has pending items.
    """
    plan_row = fetchone("SELECT * FROM plans WHERE id = ?", (plan_id,))
    if plan_row is None:
        raise NotFoundError("plan", plan_id)

    # Completion gate: all items must have resolved outcomes
    if status is not UNSET and status == PlanStatus.COMPLETED:
        pending_rows = fetchall(
            "SELECT id FROM plan_items WHERE plan_id = ? AND outcome = ?",
            (plan_id, PlanOutcome.PENDING),
        )
        if pending_rows:
            pending_ids = [row["id"] for row in pending_rows]
            raise ValidationError(
                f"Cannot complete plan: {len(pending_ids)} item(s) still have "
                f"pending outcomes: {', '.join(pending_ids)}"
            )

    fields: list[str] = []
    values: list = []

    if notes is not UNSET:
        fields.append("notes = ?")
        values.append(notes)

    if status is not UNSET:
        fields.append("status = ?")
        values.append(status)

    if not fields:
        # Nothing to change — return current state
        return get_plan(plan_id=plan_id)

    now = _now()
    fields.append("updated_at = ?")
    values.append(now)
    values.append(plan_id)

    with serialized():
        execute(
            f"UPDATE plans SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )

        action = (
            "completed"
            if status is not UNSET and status == PlanStatus.COMPLETED
            else "updated"
        )
        log_activity(
            entity_type="plan",
            entity_id=plan_id,
            action=action,
            actor=actor,
        )

        commit()

    return get_plan(plan_id=plan_id)


def delete_plan(plan_id: str, actor: str | None = None) -> bool:
    """Delete a plan and all its items (CASCADE removes plan_items automatically).

    Args:
        plan_id: Plan to delete.
        actor: Actor performing the deletion (for activity log).

    Returns:
        ``True`` if deleted, ``False`` if the plan was not found.
    """
    plan_row = fetchone("SELECT * FROM plans WHERE id = ?", (plan_id,))
    if plan_row is None:
        return False

    with serialized():
        log_activity(
            entity_type="plan",
            entity_id=plan_id,
            action="deleted",
            actor=actor,
        )
        execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        commit()

    return True


def list_plans(
    actor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Plan]:
    """List plans matching optional filters.

    Args:
        actor: Filter to plans owned by this actor.
        date_from: Include plans on or after this date.
        date_to: Include plans on or before this date.
        status: Filter by plan status (``"active"`` or ``"completed"``).
        limit: Maximum results to return (default 50).
        offset: Number of results to skip for pagination (default 0).

    Returns:
        List of ``Plan`` models ordered by date descending.
    """
    sql = "SELECT * FROM plans WHERE 1=1"
    params: list = []

    if actor is not None:
        sql += " AND actor = ?"
        params.append(actor)

    if date_from is not None:
        sql += " AND date >= ?"
        params.append(date_from.isoformat())

    if date_to is not None:
        sql += " AND date <= ?"
        params.append(date_to.isoformat())

    if status is not None:
        sql += " AND status = ?"
        params.append(status)

    sql += " ORDER BY date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = fetchall(sql, tuple(params))
    return [_row_to_plan(row) for row in rows]


# ---------------------------------------------------------------------------
# Plan item operations
# ---------------------------------------------------------------------------


def add_plan_item(
    plan_id: str,
    node_id: str,
    planned_minutes: int | None = None,
    position: int | None = None,
    actor: str | None = None,
) -> PlanItem:
    """Add a node to a plan.

    Args:
        plan_id: Target plan.
        node_id: Node to add (supports prefix matching via ``get_node``).
        planned_minutes: Optional time budget in minutes (must be >= 0).
        position: Insert position (1-indexed).  If omitted, appends at end
                  (``max_display_order + 1``).  If provided, existing items
                  at or below that position shift down by 1.
        actor: Actor performing the action (for activity log).

    Returns:
        The created ``PlanItem``.

    Raises:
        NotFoundError: If the plan or node is not found.
        ValidationError: If node type not plannable, node already in plan,
                         ``planned_minutes < 0``, or ``position < 1``.

    Notes:
        Terminal-status nodes (done, cancelled) are intentionally allowed.
        Plans may include completed work for tracking or review purposes.
    """
    plan_row = fetchone("SELECT * FROM plans WHERE id = ?", (plan_id,))
    if plan_row is None:
        raise NotFoundError("plan", plan_id)

    # Validates node exists and its type is plannable
    _validate_node_plannable(node_id)

    # Resolve full node ID in case a prefix was provided
    from taskyn.graph.nodes import get_node
    node = get_node(node_id)
    node_id = node.id  # Use canonical full ID

    if planned_minutes is not None and planned_minutes < 0:
        raise ValidationError("planned_minutes must be >= 0")

    if position is not None and position < 1:
        raise ValidationError("position must be >= 1")

    item_id = uuid4().hex
    now = _now()

    with serialized():
        if position is not None:
            _shift_items_down(plan_id, position)
            order = position
        else:
            order = _get_max_display_order(plan_id) + 1

        try:
            execute(
                """
                INSERT INTO plan_items
                    (id, plan_id, node_id, planned_minutes, display_order,
                     outcome, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_id, plan_id, node_id, planned_minutes, order,
                 PlanOutcome.PENDING, now, now),
            )
        except Exception as exc:
            if "UNIQUE constraint" in str(exc):
                raise ValidationError(
                    f"Node '{node_id}' is already in plan '{plan_id}'"
                ) from exc
            raise

        log_activity(
            entity_type="plan_item",
            entity_id=item_id,
            action="added",
            new_value=node_id,
            actor=actor,
        )

        commit()

    row = fetchone("SELECT * FROM plan_items WHERE id = ?", (item_id,))
    return _row_to_plan_item(row)


def remove_plan_item(item_id: str, actor: str | None = None) -> bool:
    """Remove an item from its plan and recompact display_order.

    Args:
        item_id: ``PlanItem`` to remove.
        actor: Actor performing the action (for activity log).

    Returns:
        ``True`` if removed, ``False`` if the item was not found.
    """
    item_row = fetchone("SELECT * FROM plan_items WHERE id = ?", (item_id,))
    if item_row is None:
        return False

    plan_id = item_row["plan_id"]

    with serialized():
        log_activity(
            entity_type="plan_item",
            entity_id=item_id,
            action="removed",
            old_value=item_row["node_id"],
            actor=actor,
        )
        execute("DELETE FROM plan_items WHERE id = ?", (item_id,))
        _recompact_display_order(plan_id)
        commit()

    return True


def reorder_plan_item(
    item_id: str,
    new_position: int,
    actor: str | None = None,
) -> PlanItem:
    """Move a plan item to a new position using the 4-step algorithm.

    Algorithm:
        1. Fetch item; record ``plan_id`` and current ``display_order``.
        2. Delete item row temporarily.
        3. Recompact remaining N-1 items (eliminates any gaps).
        4. Validate ``new_position``: must be ``>= 1`` and ``<= N`` where N is
           the total item count (original count = remaining + 1).  The upper
           bound is the ORIGINAL item count, not the post-removal count.
        5. Shift items at ``new_position`` and below down by 1.
        6. Re-insert item at ``new_position``.

    Args:
        item_id: ``PlanItem`` to move.
        new_position: Target position (1-indexed).
        actor: Actor performing the action (for activity log).

    Returns:
        Updated ``PlanItem`` with new ``display_order``.

    Raises:
        NotFoundError: If the item is not found.
        ValidationError: If ``new_position < 1`` or exceeds the item count.
    """
    item_row = fetchone("SELECT * FROM plan_items WHERE id = ?", (item_id,))
    if item_row is None:
        raise NotFoundError("plan_item", item_id)

    plan_id = item_row["plan_id"]
    old_position = item_row["display_order"]

    # Count total items NOW (before any writes) to validate the new position.
    # Valid range: 1..total.  total == remaining+1 after re-insertion.
    total_row = fetchone(
        "SELECT COUNT(*) AS cnt FROM plan_items WHERE plan_id = ?",
        (plan_id,),
    )
    total = total_row["cnt"] if total_row else 1  # at least the item itself

    if new_position < 1:
        raise ValidationError("new_position must be >= 1")
    if new_position > total:
        raise ValidationError(
            f"new_position {new_position} exceeds item count {total}"
        )

    # Snapshot item fields so we can re-insert after deletion
    snap_node_id = item_row["node_id"]
    snap_planned_minutes = item_row["planned_minutes"]
    snap_outcome = item_row["outcome"]
    snap_outcome_notes = item_row["outcome_notes"]
    snap_carried_to = item_row["carried_to_plan_id"]
    snap_created_at = item_row["created_at"]

    with serialized():
        # Step 2: delete item temporarily
        execute("DELETE FROM plan_items WHERE id = ?", (item_id,))

        # Step 3: recompact remaining N-1 items
        _recompact_display_order(plan_id)

        # Step 5: shift items at new_position and below down by 1
        _shift_items_down(plan_id, new_position)

        # Step 6: re-insert at target position
        now = _now()
        execute(
            """
            INSERT INTO plan_items
                (id, plan_id, node_id, planned_minutes, display_order,
                 outcome, outcome_notes, carried_to_plan_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, plan_id, snap_node_id, snap_planned_minutes, new_position,
             snap_outcome, snap_outcome_notes, snap_carried_to,
             snap_created_at, now),
        )

        log_activity(
            entity_type="plan_item",
            entity_id=item_id,
            action="reordered",
            old_value=str(old_position),
            new_value=str(new_position),
            actor=actor,
        )

        commit()

    row = fetchone("SELECT * FROM plan_items WHERE id = ?", (item_id,))
    return _row_to_plan_item(row)


def update_plan_item(
    item_id: str,
    planned_minutes=UNSET,
    outcome=UNSET,
    outcome_notes=UNSET,
    actor: str | None = None,
) -> PlanItem:
    """Update fields on a plan item.

    UNSET sentinel convention: pass ``UNSET`` (the default) to leave a field
    unchanged; pass ``None`` to clear a nullable field.

    Args:
        item_id: ``PlanItem`` to update.
        planned_minutes: New time budget in minutes (``None`` clears, must be >= 0).
        outcome: New outcome value (validated against ``PlanOutcome`` enum).
        outcome_notes: Freetext notes on the outcome (``None`` clears).
        actor: Actor performing the action (for activity log).

    Returns:
        Updated ``PlanItem``.

    Raises:
        NotFoundError: If the item is not found.
        ValidationError: If ``outcome`` is not a valid ``PlanOutcome`` value,
                         or ``planned_minutes < 0``.

    Activity logging:
        Logs ``outcome_set`` when the outcome changes, ``updated`` otherwise.
    """
    item_row = fetchone("SELECT * FROM plan_items WHERE id = ?", (item_id,))
    if item_row is None:
        raise NotFoundError("plan_item", item_id)

    if planned_minutes is not UNSET and planned_minutes is not None:
        if planned_minutes < 0:
            raise ValidationError("planned_minutes must be >= 0")

    if outcome is not UNSET and outcome is not None:
        valid_outcomes = {o.value for o in PlanOutcome}
        if outcome not in valid_outcomes:
            raise ValidationError(
                f"Invalid outcome '{outcome}'. "
                f"Valid values: {', '.join(sorted(valid_outcomes))}"
            )

    fields: list[str] = []
    values: list = []
    outcome_changed = False
    minutes_changed = False

    if planned_minutes is not UNSET:
        fields.append("planned_minutes = ?")
        values.append(planned_minutes)
        minutes_changed = True

    if outcome is not UNSET:
        fields.append("outcome = ?")
        values.append(outcome)
        outcome_changed = True

    if outcome_notes is not UNSET:
        fields.append("outcome_notes = ?")
        values.append(outcome_notes)

    if not fields:
        return _row_to_plan_item(item_row)

    now = _now()
    fields.append("updated_at = ?")
    values.append(now)
    values.append(item_id)

    with serialized():
        execute(
            f"UPDATE plan_items SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )

        if outcome_changed:
            log_activity(
                entity_type="plan_item",
                entity_id=item_id,
                action="outcome_set",
                old_value=str(item_row["outcome"]),
                new_value=str(outcome),
                actor=actor,
            )
        elif minutes_changed:
            log_activity(
                entity_type="plan_item",
                entity_id=item_id,
                action="updated",
                old_value=str(item_row["planned_minutes"]),
                new_value=str(planned_minutes),
                actor=actor,
            )
        else:
            log_activity(
                entity_type="plan_item",
                entity_id=item_id,
                action="updated",
                actor=actor,
            )

        commit()

    row = fetchone("SELECT * FROM plan_items WHERE id = ?", (item_id,))
    return _row_to_plan_item(row)


# ---------------------------------------------------------------------------
# Horizon views
# ---------------------------------------------------------------------------


def get_weekly_plan(
    week_start_date: date,
    actor: str | None = None,
) -> dict:
    """Get an aggregate view of daily plans for a 7-day week.

    Args:
        week_start_date: Any date in the target week.  Snaps to the Monday
                         of that week if not already a Monday.
        actor: Filter by actor.  If omitted, all actors are included and
               multiple plans can appear in the same day slot.

    Returns:
        Dict with:
            ``week_start``: date (Monday)
            ``week_end``: date (Sunday)
            ``days``: list of 7 entries (Mon–Sun), each is a ``list[plan_dict]``
                      (empty list when no plans exist; multiple dicts when
                      multiple actors have plans on the same day and no actor
                      filter is applied).
            ``summary``:
                ``total_planned_items``: int
                ``total_planned_minutes``: int
                ``outcomes``: dict[str, int] — count per ``PlanOutcome`` value
                ``actual_minutes``: int — sum of completed time entries in the week
    """
    # Snap to Monday
    monday = week_start_date - timedelta(days=week_start_date.weekday())
    sunday = monday + timedelta(days=6)

    actor_cond = " AND actor = ?" if actor is not None else ""
    actor_params: tuple = (actor,) if actor is not None else ()

    plan_rows = fetchall(
        f"SELECT * FROM plans "
        f"WHERE date BETWEEN ? AND ?{actor_cond} "
        f"ORDER BY date ASC, actor ASC",
        (monday.isoformat(), sunday.isoformat()) + actor_params,
    )

    # Group enriched plan dicts by date string (each slot is a list)
    plans_by_date: dict[str, list[dict]] = {}
    plan_ids: list[str] = []

    for row in plan_rows:
        plan_dict = get_plan(plan_id=row["id"])
        d_str = row["date"] if isinstance(row["date"], str) else row["date"].isoformat()
        plans_by_date.setdefault(d_str, []).append(plan_dict)
        plan_ids.append(row["id"])

    # Build per-day WeeklyDaySummary objects (index 0 = Monday … index 6 = Sunday)
    day_summaries: list[dict] = []
    outcome_counts: dict[str, int] = {o.value: 0 for o in PlanOutcome}
    total_planned_items = 0
    total_planned_minutes = 0

    for i in range(7):
        day = monday + timedelta(days=i)
        day_str = day.isoformat()
        day_plans = plans_by_date.get(day_str, [])

        plan_id = day_plans[0]["id"] if day_plans else None
        status = day_plans[0]["status"] if day_plans else None

        day_outcomes: dict[str, int] = {o.value: 0 for o in PlanOutcome}
        day_planned_minutes = 0
        item_count = 0

        for plan in day_plans:
            for item in plan.get("items", []):
                item_count += 1
                day_planned_minutes += item.get("planned_minutes") or 0
                oc = item.get("outcome")
                if oc:
                    day_outcomes[oc] = day_outcomes.get(oc, 0) + 1
                    outcome_counts[oc] = outcome_counts.get(oc, 0) + 1

        total_planned_items += item_count
        total_planned_minutes += day_planned_minutes

        day_summaries.append({
            "date": day_str,
            "plan_id": plan_id,
            "status": status,
            "item_count": item_count,
            "outcomes": day_outcomes,
            "planned_minutes": day_planned_minutes,
            "actual_minutes": 0,  # filled in below
        })

    # Per-day actual minutes from completed time entries during the week
    te_cond = " AND actor = ?" if actor is not None else ""
    te_params: tuple = (actor,) if actor is not None else ()
    week_start_ts = monday.isoformat() + "T00:00:00"
    week_end_ts = (sunday + timedelta(days=1)).isoformat() + "T00:00:00"

    te_rows = fetchall(
        f"""
        SELECT DATE(started_at) AS te_date,
               COALESCE(SUM(duration_minutes), 0) AS day_actual
        FROM time_entries
        WHERE started_at >= ? AND started_at < ?
          AND ended_at IS NOT NULL
          {te_cond}
        GROUP BY DATE(started_at)
        """,
        (week_start_ts, week_end_ts) + te_params,
    )
    te_by_date = {row["te_date"]: row["day_actual"] for row in te_rows}
    for ds in day_summaries:
        ds["actual_minutes"] = te_by_date.get(ds["date"], 0)

    actual_minutes = sum(ds["actual_minutes"] for ds in day_summaries)

    return {
        "week_start": monday,
        "week_end": sunday,
        "days": day_summaries,
        "summary": {
            "total_planned_items": total_planned_items,
            "total_planned_minutes": total_planned_minutes,
            "outcomes": outcome_counts,
            "actual_minutes": actual_minutes,
        },
    }


def get_monthly_plan(
    year: int,
    month: int,
    actor: str | None = None,
) -> dict:
    """Get a summary of planning activity for a calendar month.

    Args:
        year: Calendar year (e.g. 2026).
        month: Calendar month (1-12).
        actor: Filter by actor.  If omitted, aggregates all actors and
               includes a ``per_actor`` breakdown.

    Returns:
        Dict with:
            ``year``, ``month``, ``days_in_month``, ``days_with_plans``,
            ``total_planned_items``, ``total_planned_minutes``,
            ``outcomes`` (dict[str, int]),
            ``actual_minutes``,
            ``per_actor`` (list — populated only when no actor filter),
            ``milestones`` (active milestones with ``target_date`` in month).

    Notes:
        Milestones are queried with ``completed_at IS NULL`` — the
        ``completed_at`` timestamp is the source of truth for completion,
        not the ``status`` string field.
    """
    _, days_in_month = calendar.monthrange(year, month)
    first_day = date(year, month, 1)
    last_day = date(year, month, days_in_month)
    next_day = last_day + timedelta(days=1)  # exclusive upper bound for time entries

    actor_cond = " AND actor = ?" if actor is not None else ""
    actor_params: tuple = (actor,) if actor is not None else ()

    # Fetch plans for the month
    plan_rows = fetchall(
        f"SELECT id, date, actor, status FROM plans "
        f"WHERE date BETWEEN ? AND ?{actor_cond}",
        (first_day.isoformat(), last_day.isoformat()) + actor_params,
    )

    plan_ids: list[str] = []
    days_with_plans_set: set[str] = set()
    plan_actor_map: dict[str, str] = {}
    plan_date_map: dict[str, str] = {}
    plan_status_map: dict[str, str] = {}

    for row in plan_rows:
        d_str = row["date"] if isinstance(row["date"], str) else row["date"].isoformat()
        plan_ids.append(row["id"])
        days_with_plans_set.add(d_str)
        plan_actor_map[row["id"]] = row["actor"]
        plan_date_map[row["id"]] = d_str
        plan_status_map[row["id"]] = row["status"]

    # Per-day item stats (plan_id → stats)
    per_day_stats: dict[str, dict] = {}
    for plan_id in plan_ids:
        d_str = plan_date_map[plan_id]
        if d_str not in per_day_stats:
            per_day_stats[d_str] = {
                "plan_id": plan_id,
                "status": plan_status_map[plan_id],
                "item_count": 0,
                "outcomes": {o.value: 0 for o in PlanOutcome},
                "planned_minutes": 0,
                "actual_minutes": 0,
            }

    # Aggregate plan item statistics
    outcome_counts: dict[str, int] = {o.value: 0 for o in PlanOutcome}
    total_planned_items = 0
    total_planned_minutes = 0
    per_actor_data: dict[str, dict] = {}

    if plan_ids:
        placeholders = ",".join("?" * len(plan_ids))
        item_rows = fetchall(
            f"SELECT plan_id, outcome, planned_minutes "
            f"FROM plan_items WHERE plan_id IN ({placeholders})",
            tuple(plan_ids),
        )
        for row in item_rows:
            total_planned_items += 1
            total_planned_minutes += row["planned_minutes"] or 0
            oc = row["outcome"]
            outcome_counts[oc] = outcome_counts.get(oc, 0) + 1

            # Per-day stats
            d_str = plan_date_map.get(row["plan_id"])
            if d_str and d_str in per_day_stats:
                per_day_stats[d_str]["item_count"] += 1
                per_day_stats[d_str]["planned_minutes"] += row["planned_minutes"] or 0
                per_day_stats[d_str]["outcomes"][oc] = (
                    per_day_stats[d_str]["outcomes"].get(oc, 0) + 1
                )

            if actor is None:
                a = plan_actor_map.get(row["plan_id"], "unknown")
                if a not in per_actor_data:
                    per_actor_data[a] = {
                        "actor": a,
                        "days_with_plans": 0,
                        "total_planned_items": 0,
                        "total_planned_minutes": 0,
                        "outcomes": {o.value: 0 for o in PlanOutcome},
                        "actual_minutes": 0,
                        "_plan_dates": set(),
                    }
                per_actor_data[a]["total_planned_items"] += 1
                per_actor_data[a]["total_planned_minutes"] += row["planned_minutes"] or 0
                per_actor_data[a]["outcomes"][oc] = (
                    per_actor_data[a]["outcomes"].get(oc, 0) + 1
                )
                d = plan_date_map.get(row["plan_id"])
                if d:
                    per_actor_data[a]["_plan_dates"].add(d)

    # Finalise per-actor days_with_plans
    if actor is None:
        for a_data in per_actor_data.values():
            a_data["days_with_plans"] = len(a_data.pop("_plan_dates"))

    # Actual minutes from completed time entries in the month
    month_start_ts = first_day.isoformat() + "T00:00:00"
    month_end_ts = next_day.isoformat() + "T00:00:00"
    te_cond = " AND actor = ?" if actor is not None else ""
    te_params: tuple = (actor,) if actor is not None else ()

    te_rows_month = fetchall(
        f"""
        SELECT DATE(started_at) AS te_date,
               COALESCE(SUM(duration_minutes), 0) AS day_actual
        FROM time_entries
        WHERE started_at >= ? AND started_at < ?
          AND ended_at IS NOT NULL
          {te_cond}
        GROUP BY DATE(started_at)
        """,
        (month_start_ts, month_end_ts) + te_params,
    )
    te_by_date_month = {row["te_date"]: row["day_actual"] for row in te_rows_month}
    for d_str, ds in per_day_stats.items():
        ds["actual_minutes"] = te_by_date_month.get(d_str, 0)

    actual_minutes = sum(row["day_actual"] for row in te_rows_month)

    # Per-actor actual minutes (only when not filtering by actor)
    if actor is None and per_actor_data:
        actor_te_rows = fetchall(
            """
            SELECT actor, COALESCE(SUM(duration_minutes), 0) AS total
            FROM time_entries
            WHERE started_at >= ? AND started_at < ?
              AND ended_at IS NOT NULL
            GROUP BY actor
            """,
            (month_start_ts, month_end_ts),
        )
        for row in actor_te_rows:
            a = row["actor"]
            if a in per_actor_data:
                per_actor_data[a]["actual_minutes"] = row["total"]

    # Milestones with target_date in month that have NOT been completed.
    # NOTE: uses completed_at IS NULL — the completion timestamp is the
    # source of truth, NOT status = 'open' (W8 fix).
    milestone_rows = fetchall(
        """
        SELECT m.id, m.name, m.project_id, m.target_date, m.status,
               p.name AS project_name
        FROM milestones m
        JOIN projects p ON m.project_id = p.id
        WHERE m.target_date BETWEEN ? AND ?
          AND m.completed_at IS NULL
        """,
        (first_day.isoformat(), last_day.isoformat()),
    )

    milestones = [
        {
            "id": row["id"],
            "name": row["name"],
            "project_id": row["project_id"],
            "project_name": row["project_name"],
            "target_date": _parse_date(row["target_date"]),
            "status": row["status"],
        }
        for row in milestone_rows
    ]

    # Build sorted per-day list for calendar grid
    days_list = sorted(
        [{"date": d_str, **stats} for d_str, stats in per_day_stats.items()],
        key=lambda x: x["date"],
    )

    return {
        "year": year,
        "month": month,
        "days_in_month": days_in_month,
        "days_with_plans": len(days_with_plans_set),
        "total_planned_items": total_planned_items,
        "total_planned_minutes": total_planned_minutes,
        "outcomes": outcome_counts,
        "actual_minutes": actual_minutes,
        "days": days_list,
        "per_actor": list(per_actor_data.values()) if actor is None else [],
        "milestones": milestones,
    }


# ---------------------------------------------------------------------------
# Plan vs Actual
# ---------------------------------------------------------------------------


def plan_vs_actual(
    plan_date: date,
    actor: str,
) -> dict:
    """Compare planned work against actual execution for a specific day.

    Time entries are matched by ``date(started_at)``.  An entry that spans
    midnight counts entirely toward the start date — this is known behaviour,
    not a bug (W5 / documented limitation).

    Args:
        plan_date: The date to compare.
        actor: The actor whose plan and time entries to examine.  Required.

    Returns:
        Dict with:
            ``date``, ``actor``,
            ``planned_items`` (list — one entry per item in the plan),
            ``unplanned_items`` (list — nodes with time on that date but not in
                                 the plan),
            ``summary`` (aggregated totals and delta).
    """
    plan = get_plan(plan_date=plan_date, actor=actor)

    planned_node_ids: set[str] = set()
    planned_items: list[dict] = []
    total_planned_minutes = 0
    total_actual_minutes = 0
    completed_count = 0
    has_any_planned_minutes = False

    if plan:
        for item in plan["items"]:
            node_id = item.get("node_id")
            if node_id is None:
                continue  # Deleted nodes carry no time entries

            planned_node_ids.add(node_id)

            # Actual minutes for this node on this date
            te_row = fetchone(
                """
                SELECT COALESCE(SUM(duration_minutes), 0) AS actual
                FROM time_entries
                WHERE node_id = ? AND actor = ? AND date(started_at) = ?
                  AND ended_at IS NOT NULL
                """,
                (node_id, actor, plan_date.isoformat()),
            )
            actual_mins = te_row["actual"] if te_row else 0

            pm = item.get("planned_minutes")
            delta = (actual_mins - pm) if pm is not None else None

            if pm is not None:
                has_any_planned_minutes = True
                total_planned_minutes += pm

            total_actual_minutes += actual_mins

            # Determine if the node has reached a terminal status
            is_terminal = False
            try:
                from taskyn.graph.nodes import get_node
                from taskyn.core.project import get_project
                from taskyn.methodologies import get_methodology

                node_obj = get_node(node_id)
                if node_obj:
                    proj = get_project(node_obj.project_id)
                    if proj:
                        meth = get_methodology(proj.methodology)
                        if meth:
                            nt_def = meth.get_node_type(node_obj.node_type)
                            if nt_def:
                                is_terminal = node_obj.status in nt_def.terminal_statuses
            except Exception:
                pass  # Best-effort — don't let methodology errors break comparison

            if item.get("outcome") == PlanOutcome.COMPLETED:
                completed_count += 1

            planned_items.append({
                "node_id": node_id,
                "title": item.get("node_title"),
                "planned_minutes": pm,
                "display_order": item.get("display_order"),
                "actual_minutes": actual_mins,
                "current_status": item.get("node_status"),
                "is_terminal": is_terminal,
                "delta_minutes": delta,
                "outcome": item.get("outcome"),
                "outcome_notes": item.get("outcome_notes"),
            })

    # Surface unplanned work: time entries on this date for this actor
    # that are NOT in the plan.
    all_te_rows = fetchall(
        """
        SELECT
            te.node_id,
            COALESCE(SUM(te.duration_minutes), 0) AS actual,
            n.title      AS node_title,
            n.status     AS node_status,
            n.project_id AS project_id,
            p.name       AS project_name
        FROM time_entries te
        LEFT JOIN nodes n ON te.node_id = n.id
        LEFT JOIN projects p ON n.project_id = p.id
        WHERE te.actor = ? AND date(te.started_at) = ?
          AND te.ended_at IS NOT NULL
        GROUP BY te.node_id
        """,
        (actor, plan_date.isoformat()),
    )

    unplanned_items: list[dict] = []
    total_unplanned_minutes = 0
    for row in all_te_rows:
        nid = row["node_id"]
        if nid not in planned_node_ids:
            mins = row["actual"]
            total_unplanned_minutes += mins
            unplanned_items.append({
                "node_id": nid,
                "title": row["node_title"],
                "actual_minutes": mins,
                "current_status": row["node_status"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
            })

    overall_delta = (
        (total_actual_minutes - total_planned_minutes)
        if has_any_planned_minutes
        else None
    )

    return {
        "date": plan_date,
        "actor": actor,
        "planned_items": planned_items,
        "unplanned_items": unplanned_items,
        "summary": {
            "total_planned_minutes": total_planned_minutes,
            "total_actual_minutes": total_actual_minutes,
            "total_unplanned_minutes": total_unplanned_minutes,
            "planned_item_count": len(planned_items),
            "completed_count": completed_count,
            "unplanned_item_count": len(unplanned_items),
            "overall_delta": overall_delta,
        },
    }


# ---------------------------------------------------------------------------
# Carry Over
# ---------------------------------------------------------------------------


def carry_over_plan(
    source_plan_id: str,
    target_date: date,
    item_ids: list[str] | None = None,
    actor: str | None = None,
) -> dict:
    """Carry incomplete items from one plan to another.

    For each carried item:
        1. A new ``PlanItem`` is created in the target plan with the same
           ``node_id`` and ``planned_minutes``, outcome reset to ``pending``.
        2. The source item's ``outcome`` is updated to ``carried_over``.
        3. The source item's ``carried_to_plan_id`` is set to the target plan ID.

    Args:
        source_plan_id: Plan to carry items from.
        target_date: Date for the target plan.  The target plan is created if
                     it doesn't exist (inherits actor from source).  Items are
                     appended after any existing items when the target plan
                     already exists.
        item_ids: Specific ``PlanItem`` IDs to carry.  If ``None``, carries
                  all items with ``outcome in ('pending', 'partial')``.
        actor: Actor performing the action (for activity log).

    Returns:
        Dict with ``source_plan_id``, ``target_plan`` (full ``get_plan`` dict),
        ``carried_count``, and ``skipped`` (list of dicts with
        ``item_id``, ``node_id``, ``reason``).

    Raises:
        NotFoundError: If the source plan is not found.
        ValidationError: If ``target_date <= source plan's date``.

    Notes:
        Carrying to a past date that is still after the source date is allowed
        — this supports retroactive plan reconstruction (W7).
    """
    source_row = fetchone("SELECT * FROM plans WHERE id = ?", (source_plan_id,))
    if source_row is None:
        raise NotFoundError("plan", source_plan_id)

    source_date = _parse_date(source_row["date"])
    source_actor = source_row["actor"]

    if target_date <= source_date:
        raise ValidationError(
            f"target_date ({target_date}) must be strictly after "
            f"source plan date ({source_date})"
        )

    # Fetch all source items
    source_items = fetchall(
        "SELECT * FROM plan_items WHERE plan_id = ?",
        (source_plan_id,),
    )
    source_item_map: dict[str, object] = {row["id"]: row for row in source_items}

    skipped: list[dict] = []
    items_to_carry: list = []

    if item_ids is not None:
        for iid in item_ids:
            if iid not in source_item_map:
                skipped.append({"item_id": iid, "node_id": None, "reason": "not_found"})
                continue
            row = source_item_map[iid]
            if row["outcome"] in (PlanOutcome.COMPLETED, PlanOutcome.DROPPED):
                skipped.append({
                    "item_id": iid,
                    "node_id": row["node_id"],
                    "reason": "already_resolved",
                })
            elif row["outcome"] == PlanOutcome.CARRIED_OVER:
                # Already carried to another plan — re-carrying would corrupt the chain
                skipped.append({
                    "item_id": iid,
                    "node_id": row["node_id"],
                    "reason": "already_carried",
                })
            else:
                items_to_carry.append(row)
    else:
        for row in source_items:
            if row["outcome"] in (PlanOutcome.COMPLETED, PlanOutcome.DROPPED):
                skipped.append({
                    "item_id": row["id"],
                    "node_id": row["node_id"],
                    "reason": "already_resolved",
                })
            elif row["outcome"] in (PlanOutcome.PENDING, PlanOutcome.PARTIAL):
                items_to_carry.append(row)
            # carried_over items are silently ignored — already processed

    # Get or create the target plan
    target_plan_row = fetchone(
        "SELECT * FROM plans WHERE date = ? AND actor = ?",
        (target_date.isoformat(), source_actor),
    )

    with serialized():
        now = _now()

        if target_plan_row is None:
            target_plan_id = uuid4().hex
            execute(
                """
                INSERT INTO plans (id, date, actor, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (target_plan_id, target_date.isoformat(), source_actor,
                 PlanStatus.ACTIVE, now, now),
            )
            log_activity(
                entity_type="plan",
                entity_id=target_plan_id,
                action="plan_created",
                actor=actor,
            )
            commit()
        else:
            target_plan_id = target_plan_row["id"]

        # Current maximum display_order in target plan
        max_order = _get_max_display_order(target_plan_id)

        # Existing node_ids in target plan — used to detect duplicates
        existing_rows = fetchall(
            "SELECT node_id FROM plan_items "
            "WHERE plan_id = ? AND node_id IS NOT NULL",
            (target_plan_id,),
        )
        existing_node_ids: set[str] = {row["node_id"] for row in existing_rows}

        carried_count = 0

        for item_row in items_to_carry:
            node_id = item_row["node_id"]

            # Skip if this node is already in the target plan
            if node_id is not None and node_id in existing_node_ids:
                skipped.append({
                    "item_id": item_row["id"],
                    "node_id": node_id,
                    "reason": "already_in_target",
                })
                continue

            # Create new PlanItem in target plan
            max_order += 1
            new_item_id = uuid4().hex
            execute(
                """
                INSERT INTO plan_items
                    (id, plan_id, node_id, planned_minutes, display_order,
                     outcome, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (new_item_id, target_plan_id, node_id,
                 item_row["planned_minutes"], max_order,
                 PlanOutcome.PENDING, now, now),
            )

            if node_id is not None:
                existing_node_ids.add(node_id)

            # Mark source item as carried over
            execute(
                """
                UPDATE plan_items
                SET outcome = ?, carried_to_plan_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (PlanOutcome.CARRIED_OVER, target_plan_id, now, item_row["id"]),
            )

            log_activity(
                entity_type="plan_item",
                entity_id=item_row["id"],
                action="carried_over",
                new_value=target_plan_id,
                actor=actor,
            )

            carried_count += 1

        commit()

    return {
        "source_plan_id": source_plan_id,
        "target_plan": get_plan(plan_id=target_plan_id),
        "carried_count": carried_count,
        "skipped": skipped,
    }
