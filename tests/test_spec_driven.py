"""Tests for spec-driven methodology v3.

Tests cover:
- 5 node types and their status workflows
- Parent pair validation (3-level hierarchy)
- Strict phase gating (requirement → design → task)
- Time tracking enforcement (only on todos)
- Helper methods
"""

import pytest

from taskyn.db.enums import Methodology
from taskyn.methodologies import get_methodology, list_methodologies
from taskyn.core import create_company, create_project
from taskyn.core.time_entry import start_timer, stop_timer, log_time
from taskyn.graph import create_node, create_edge, update_node
from taskyn.exceptions import ValidationError


# ============================================================
# Methodology Registration
# ============================================================


def test_spec_driven_methodology_registered():
    """Test that spec_driven methodology is registered."""
    methodology = get_methodology("spec_driven")
    assert methodology is not None
    assert methodology.name == "spec_driven"
    assert methodology.display_name == "Spec-Driven"


def test_spec_driven_in_list():
    """Test spec_driven appears in methodology list."""
    methodologies = list_methodologies()
    names = [m.name for m in methodologies]
    assert "spec_driven" in names
    assert "classic_agile" in names


# ============================================================
# Node Types
# ============================================================


def test_spec_driven_node_types():
    """Test spec_driven v3 has exactly 5 node types."""
    methodology = get_methodology("spec_driven")
    node_types = methodology.node_types

    expected = ["spec", "requirement", "design", "task", "todo"]
    for nt in expected:
        assert nt in node_types, f"Missing node type: {nt}"
    assert len(node_types) == 5


def test_spec_driven_edge_types():
    """Test spec_driven has correct edge types."""
    methodology = get_methodology("spec_driven")
    edge_types = methodology.edge_types

    assert "parent" in edge_types
    assert "sequence" in edge_types
    assert "depends_on" in edge_types
    assert "blocks" in edge_types
    assert len(edge_types) == 4


# ============================================================
# Status Workflows — Phase Nodes
# ============================================================


def test_spec_workflow(temp_db):
    """Test spec: draft → active → done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature X")
    assert spec.status == "draft"

    spec = update_node(spec.id, status="active")
    assert spec.status == "active"

    spec = update_node(spec.id, status="done")
    assert spec.status == "done"


def test_spec_cancelled(temp_db):
    """Test spec can be cancelled from draft or active."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    # Cancel from draft
    spec1 = create_node(project.id, "spec", "Cancel Draft")
    spec1 = update_node(spec1.id, status="cancelled")
    assert spec1.status == "cancelled"

    # Cancel from active
    spec2 = create_node(project.id, "spec", "Cancel Active")
    spec2 = update_node(spec2.id, status="active")
    spec2 = update_node(spec2.id, status="cancelled")
    assert spec2.status == "cancelled"


def test_requirement_workflow(temp_db):
    """Test requirement: draft → active → done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    req = create_node(project.id, "requirement", "User can login")
    assert req.status == "draft"

    # No parent, so no gating — can go active directly
    req = update_node(req.id, status="active")
    assert req.status == "active"

    req = update_node(req.id, status="done")
    assert req.status == "done"


def test_design_workflow(temp_db):
    """Test design: draft → active → done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    design = create_node(project.id, "design", "Auth Architecture")
    assert design.status == "draft"

    # No parent, so no gating
    design = update_node(design.id, status="active")
    assert design.status == "active"

    design = update_node(design.id, status="done")
    assert design.status == "done"


def test_task_workflow(temp_db):
    """Test task: draft → active → done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    task = create_node(project.id, "task", "Frontend Auth")
    assert task.status == "draft"

    # No parent, so no gating
    task = update_node(task.id, status="active")
    assert task.status == "active"

    task = update_node(task.id, status="done")
    assert task.status == "done"


def test_phase_any_to_any_transitions(temp_db):
    """Phase nodes can transition to any valid status — no gate on direction."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    assert spec.status == "draft"

    # Skip forward: draft → done
    spec = update_node(spec.id, status="done")
    assert spec.status == "done"

    # Backward: done → draft (reopen)
    spec = update_node(spec.id, status="draft")
    assert spec.status == "draft"

    # Skip: draft → active → back to draft
    spec = update_node(spec.id, status="active")
    spec = update_node(spec.id, status="draft")
    assert spec.status == "draft"


# ============================================================
# Status Workflows — Todo Nodes
# ============================================================


def test_todo_workflow(temp_db):
    """Test todo: todo → in_progress → done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    todo = create_node(project.id, "todo", "Write user stories")
    assert todo.status == "todo"

    todo = update_node(todo.id, status="in_progress")
    assert todo.status == "in_progress"

    todo = update_node(todo.id, status="done")
    assert todo.status == "done"


def test_todo_cancelled(temp_db):
    """Test todo can be cancelled from todo or in_progress."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    # Cancel from todo
    t1 = create_node(project.id, "todo", "Cancel Todo")
    t1 = update_node(t1.id, status="cancelled")
    assert t1.status == "cancelled"

    # Cancel from in_progress
    t2 = create_node(project.id, "todo", "Cancel InProgress")
    t2 = update_node(t2.id, status="in_progress")
    t2 = update_node(t2.id, status="cancelled")
    assert t2.status == "cancelled"


def test_todo_any_to_any_transitions(temp_db):
    """Todo nodes can transition to any valid status — no gate on direction."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    todo = create_node(project.id, "todo", "A task")
    assert todo.status == "todo"

    # Skip forward: todo → done directly
    todo = update_node(todo.id, status="done")
    assert todo.status == "done"

    # Backward: done → todo (reopen)
    todo = update_node(todo.id, status="todo")
    assert todo.status == "todo"


# ============================================================
# Parent Pair Validation
# ============================================================


def test_valid_parent_pairs(temp_db):
    """Test that valid parent-child relationships are accepted."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    req = create_node(project.id, "requirement", "Req")
    design = create_node(project.id, "design", "Design")
    task = create_node(project.id, "task", "Task")
    todo1 = create_node(project.id, "todo", "Todo under Req")
    todo2 = create_node(project.id, "todo", "Todo under Design")
    todo3 = create_node(project.id, "todo", "Todo under Task")

    # All valid parent relationships
    create_edge(req.id, spec.id, "parent")      # requirement → spec
    create_edge(design.id, spec.id, "parent")    # design → spec
    create_edge(task.id, spec.id, "parent")      # task → spec
    create_edge(todo1.id, req.id, "parent")      # todo → requirement
    create_edge(todo2.id, design.id, "parent")   # todo → design
    create_edge(todo3.id, task.id, "parent")     # todo → task


def test_invalid_parent_pairs(temp_db):
    """Test that invalid parent-child relationships are rejected."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    req = create_node(project.id, "requirement", "Req")
    design = create_node(project.id, "design", "Design")
    task = create_node(project.id, "task", "Task")
    todo = create_node(project.id, "todo", "Todo")

    # requirement can only parent under spec, not under design or task
    with pytest.raises(ValidationError):
        create_edge(req.id, design.id, "parent")

    # design can only parent under spec, not under requirement
    with pytest.raises(ValidationError):
        create_edge(design.id, req.id, "parent")

    # task can only parent under spec, not under requirement
    with pytest.raises(ValidationError):
        create_edge(task.id, req.id, "parent")

    # todo can only parent under requirement/design/task, not under spec
    with pytest.raises(ValidationError):
        create_edge(todo.id, spec.id, "parent")


def test_invalid_node_types_rejected(temp_db):
    """Test that v2 node types are no longer valid."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    for invalid_type in ["implementation", "e2e_verification", "functional_verification", "unit_verification"]:
        with pytest.raises(ValidationError, match="Invalid node type"):
            create_node(project.id, invalid_type, f"Invalid {invalid_type}")


# ============================================================
# Strict Phase Gating
# ============================================================


def test_gating_requirement_needs_active_spec(temp_db):
    """Test: requirement can go active only when parent spec is active."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    req = create_node(project.id, "requirement", "Req")
    create_edge(req.id, spec.id, "parent")

    # Spec is draft — requirement cannot activate
    with pytest.raises(ValidationError, match="must be active or done"):
        update_node(req.id, status="active")

    # Activate spec — now requirement can activate
    update_node(spec.id, status="active")
    req = update_node(req.id, status="active")
    assert req.status == "active"


def test_gating_design_needs_done_requirements(temp_db):
    """Test: design can go active only when ALL sibling requirements are done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    update_node(spec.id, status="active")

    req1 = create_node(project.id, "requirement", "Req 1")
    req2 = create_node(project.id, "requirement", "Req 2")
    design = create_node(project.id, "design", "Design")

    create_edge(req1.id, spec.id, "parent")
    create_edge(req2.id, spec.id, "parent")
    create_edge(design.id, spec.id, "parent")

    # Requirements not done — design cannot activate
    update_node(req1.id, status="active")
    with pytest.raises(ValidationError, match="all requirements must be done"):
        update_node(design.id, status="active")

    # Complete req1 but not req2 — still blocked
    update_node(req1.id, status="done")
    update_node(req2.id, status="active")
    with pytest.raises(ValidationError, match="all requirements must be done"):
        update_node(design.id, status="active")

    # Complete req2 — now design can activate
    update_node(req2.id, status="done")
    design = update_node(design.id, status="active")
    assert design.status == "active"


def test_gating_task_needs_done_designs(temp_db):
    """Test: task can go active only when ALL sibling designs are done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    update_node(spec.id, status="active")

    req = create_node(project.id, "requirement", "Req")
    create_edge(req.id, spec.id, "parent")
    update_node(req.id, status="active")
    update_node(req.id, status="done")

    design = create_node(project.id, "design", "Design")
    task = create_node(project.id, "task", "Frontend")

    create_edge(design.id, spec.id, "parent")
    create_edge(task.id, spec.id, "parent")

    # Design not done — task cannot activate
    with pytest.raises(ValidationError, match="all designs must be done"):
        update_node(task.id, status="active")

    # Complete design — now task can activate
    update_node(design.id, status="active")
    update_node(design.id, status="done")

    task = update_node(task.id, status="active")
    assert task.status == "active"


def test_gating_todo_needs_active_parent(temp_db):
    """Test: todo can start only when parent phase is active or done."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    req = create_node(project.id, "requirement", "Req")
    todo = create_node(project.id, "todo", "Write stories")
    create_edge(todo.id, req.id, "parent")

    # Requirement is draft — todo cannot start
    with pytest.raises(ValidationError, match="must be active or done"):
        update_node(todo.id, status="in_progress")

    # Activate requirement — now todo can start
    update_node(req.id, status="active")
    todo = update_node(todo.id, status="in_progress")
    assert todo.status == "in_progress"


def test_gating_no_parent_allows_activation(temp_db):
    """Test: nodes without parents can activate freely (no gating)."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    # Standalone nodes with no parent — should activate without issues
    req = create_node(project.id, "requirement", "Standalone Req")
    req = update_node(req.id, status="active")
    assert req.status == "active"

    design = create_node(project.id, "design", "Standalone Design")
    design = update_node(design.id, status="active")
    assert design.status == "active"


def test_gating_cancelled_requirements_count_as_done(temp_db):
    """Test: cancelled requirements are terminal, so design can proceed."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    update_node(spec.id, status="active")

    req = create_node(project.id, "requirement", "Cancelled Req")
    design = create_node(project.id, "design", "Design")

    create_edge(req.id, spec.id, "parent")
    create_edge(design.id, spec.id, "parent")

    # Cancel requirement (terminal status)
    update_node(req.id, status="cancelled")

    # Design should be able to activate
    design = update_node(design.id, status="active")
    assert design.status == "active"


# ============================================================
# Time Tracking Enforcement
# ============================================================


def test_time_tracking_allowed_on_todo(temp_db):
    """Test that time tracking is allowed on todo nodes."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    todo = create_node(project.id, "todo", "Work item")
    entry = start_timer(todo.id)
    assert entry is not None
    stopped = stop_timer()
    assert stopped is not None


def test_time_tracking_blocked_on_phase_nodes(temp_db):
    """Test that time tracking is blocked on all phase nodes."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    for node_type in ["spec", "requirement", "design", "task"]:
        node = create_node(project.id, node_type, f"Phase {node_type}")
        with pytest.raises(ValidationError, match="Time tracking"):
            start_timer(node.id)


def test_log_time_on_todo(temp_db):
    """Test manual time logging on todo nodes."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    todo = create_node(project.id, "todo", "Research")
    entry = log_time(todo.id, 45, notes="Research session")
    assert entry.duration_minutes == 45


def test_log_time_blocked_on_phase(temp_db):
    """Test manual time logging is blocked on phase nodes."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    spec = create_node(project.id, "spec", "Feature")
    with pytest.raises(ValidationError, match="Time tracking"):
        log_time(spec.id, 30)


# ============================================================
# Helper Methods
# ============================================================


def test_helper_get_story_type():
    """Test get_story_type returns 'spec'."""
    methodology = get_methodology("spec_driven")
    assert methodology.get_story_type() == "spec"


def test_helper_get_task_type():
    """Test get_task_type returns 'todo'."""
    methodology = get_methodology("spec_driven")
    assert methodology.get_task_type() == "todo"


def test_helper_get_in_progress_status():
    """Test get_in_progress_status for all node types."""
    methodology = get_methodology("spec_driven")
    # Phase nodes use 'active'
    assert methodology.get_in_progress_status("spec") == "active"
    assert methodology.get_in_progress_status("requirement") == "active"
    assert methodology.get_in_progress_status("design") == "active"
    assert methodology.get_in_progress_status("task") == "active"
    # Todo uses 'in_progress'
    assert methodology.get_in_progress_status("todo") == "in_progress"


def test_helper_get_done_status():
    """Test get_done_status returns 'done' for all types."""
    methodology = get_methodology("spec_driven")
    for nt in ["spec", "requirement", "design", "task", "todo"]:
        assert methodology.get_done_status(nt) == "done"


def test_helper_can_track_time():
    """Test can_track_time flags."""
    methodology = get_methodology("spec_driven")
    # Only todo can track time
    assert methodology.get_node_type("todo").can_track_time is True
    for nt in ["spec", "requirement", "design", "task"]:
        assert methodology.get_node_type(nt).can_track_time is False


# ============================================================
# Full Workflow Integration
# ============================================================


def test_full_workflow(temp_db):
    """Test complete spec-driven v3 workflow with gating."""
    company = create_company("Test Co")
    project = create_project(company.id, "P", Methodology.SPEC_DRIVEN)

    # Create spec and activate
    spec = create_node(project.id, "spec", "User Auth")
    update_node(spec.id, status="active")

    # Create requirement under spec
    req = create_node(project.id, "requirement", "OAuth2 Login")
    create_edge(req.id, spec.id, "parent")

    # Create todo under requirement
    req_todo = create_node(project.id, "todo", "Write user stories")
    create_edge(req_todo.id, req.id, "parent")

    # Activate requirement, work on todo
    update_node(req.id, status="active")
    update_node(req_todo.id, status="in_progress")
    entry = start_timer(req_todo.id)
    stop_timer()
    update_node(req_todo.id, status="done")
    update_node(req.id, status="done")

    # Create design — should now be allowed to activate
    design = create_node(project.id, "design", "Auth Architecture")
    create_edge(design.id, spec.id, "parent")

    design_todo = create_node(project.id, "todo", "Draw diagrams")
    create_edge(design_todo.id, design.id, "parent")

    update_node(design.id, status="active")
    update_node(design_todo.id, status="in_progress")
    update_node(design_todo.id, status="done")
    update_node(design.id, status="done")

    # Create task — should now be allowed to activate
    task = create_node(project.id, "task", "Frontend Auth Flow")
    create_edge(task.id, spec.id, "parent")

    task_todo1 = create_node(project.id, "todo", "Login form")
    task_todo2 = create_node(project.id, "todo", "Write tests")
    create_edge(task_todo1.id, task.id, "parent")
    create_edge(task_todo2.id, task.id, "parent")

    update_node(task.id, status="active")

    # Work on todos
    update_node(task_todo1.id, status="in_progress")
    update_node(task_todo1.id, status="done")
    update_node(task_todo2.id, status="in_progress")
    update_node(task_todo2.id, status="done")

    # Complete task and spec
    update_node(task.id, status="done")
    update_node(spec.id, status="done")

    # Verify final states
    from taskyn.graph import get_node
    assert get_node(spec.id).status == "done"
    assert get_node(req.id).status == "done"
    assert get_node(design.id).status == "done"
    assert get_node(task.id).status == "done"
