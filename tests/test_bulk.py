"""Tests for bulk operations."""

import pytest

from taskyn.core import (
    create_company,
    create_project,
    create_story,
    create_task,
    create_milestone,
    start_node,
    get_node_tags,
    BulkResult,
    bulk_move_to_milestone,
    bulk_update_status,
    bulk_reassign,
    bulk_tag,
    bulk_delete,
    bulk_update_priority,
)
from taskyn.graph import get_node
from taskyn.exceptions import ValidationError


@pytest.fixture
def project(temp_db):
    """Create a test project."""
    company = create_company("Test Company")
    return create_project(company.id, "Test Project")


@pytest.fixture
def tasks(project):
    """Create test tasks."""
    story = create_story(project.id, title="Test Story")
    task1 = create_task(story.id, title="Task 1")
    task2 = create_task(story.id, title="Task 2")
    task3 = create_task(story.id, title="Task 3")
    return [task1, task2, task3]


def test_bulk_move_to_milestone(project, tasks):
    """Test moving multiple nodes to a milestone."""
    milestone = create_milestone(project.id, name="Sprint 1")
    node_ids = [t.id for t in tasks]

    result = bulk_move_to_milestone(node_ids, milestone.id, actor="pm")

    assert isinstance(result, BulkResult)
    assert len(result.succeeded) == 3
    assert len(result.failed) == 0

    # Verify all nodes are in the milestone
    for task_id in node_ids:
        node = get_node(task_id)
        assert node.milestone_id == milestone.id


def test_bulk_move_to_milestone_remove(project, tasks):
    """Test removing nodes from milestone (set to None)."""
    milestone = create_milestone(project.id, name="Sprint 1")
    node_ids = [t.id for t in tasks]

    # First assign to milestone
    bulk_move_to_milestone(node_ids, milestone.id)

    # Then remove from milestone
    result = bulk_move_to_milestone(node_ids, None, actor="pm")

    assert len(result.succeeded) == 3

    for task_id in node_ids:
        node = get_node(task_id)
        assert node.milestone_id is None


def test_bulk_move_with_invalid_node(project, tasks):
    """Test bulk move with some invalid nodes."""
    milestone = create_milestone(project.id, name="Sprint 1")
    node_ids = [tasks[0].id, "nonexistent", tasks[1].id]

    result = bulk_move_to_milestone(node_ids, milestone.id)

    assert len(result.succeeded) == 2
    assert len(result.failed) == 1
    assert result.failed[0][0] == "nonexistent"


def test_bulk_update_status(tasks):
    """Test updating status of multiple nodes."""
    node_ids = [t.id for t in tasks]

    # Start all tasks
    result = bulk_update_status(node_ids, "in_progress", actor="developer")

    assert len(result.succeeded) == 3
    assert len(result.failed) == 0

    for task_id in node_ids:
        node = get_node(task_id)
        assert node.status == "in_progress"


def test_bulk_update_status_skip_forward(tasks):
    """Bulk status update allows skip-forward transitions (todo → done)."""
    node_ids = [t.id for t in tasks]

    # Skip forward: todo → done directly — all should succeed now
    result = bulk_update_status(node_ids, "done")

    assert len(result.succeeded) == 3
    assert len(result.failed) == 0


def test_bulk_update_status_invalid_status_name(tasks):
    """Bulk status update rejects entirely unknown status names."""
    node_ids = [t.id for t in tasks]

    result = bulk_update_status(node_ids, "nonexistent_status")

    # All should fail — invalid status name
    assert len(result.succeeded) == 0
    assert len(result.failed) == 3


def test_bulk_reassign(tasks):
    """Test reassigning multiple nodes."""
    node_ids = [t.id for t in tasks]

    result = bulk_reassign(node_ids, "alice", actor="pm")

    assert len(result.succeeded) == 3
    assert len(result.failed) == 0

    for task_id in node_ids:
        node = get_node(task_id)
        assert node.assignee == "alice"


def test_bulk_reassign_unassign(tasks):
    """Test unassigning multiple nodes."""
    node_ids = [t.id for t in tasks]

    # First assign
    bulk_reassign(node_ids, "alice")

    # Then unassign
    result = bulk_reassign(node_ids, None, actor="pm")

    assert len(result.succeeded) == 3

    for task_id in node_ids:
        node = get_node(task_id)
        assert node.assignee is None


def test_bulk_tag(tasks):
    """Test tagging multiple nodes."""
    node_ids = [t.id for t in tasks]

    result = bulk_tag(node_ids, "urgent", actor="pm")

    assert len(result.succeeded) == 3
    assert len(result.failed) == 0

    for task_id in node_ids:
        tags = get_node_tags(task_id)
        tag_names = [t.name for t in tags]
        assert "urgent" in tag_names


def test_bulk_tag_with_invalid_node(tasks):
    """Test bulk tagging with some invalid nodes."""
    node_ids = [tasks[0].id, "nonexistent", tasks[1].id]

    result = bulk_tag(node_ids, "urgent")

    assert len(result.succeeded) == 2
    assert len(result.failed) == 1


def test_bulk_delete(tasks):
    """Test deleting multiple nodes."""
    node_ids = [t.id for t in tasks]

    result = bulk_delete(node_ids, actor="admin")

    assert len(result.succeeded) == 3
    assert len(result.failed) == 0

    for task_id in node_ids:
        node = get_node(task_id)
        assert node is None


def test_bulk_delete_idempotent(tasks):
    """Test that bulk delete handles already-deleted nodes."""
    node_ids = [t.id for t in tasks]

    # Delete once
    bulk_delete(node_ids)

    # Delete again
    result = bulk_delete(node_ids)

    # All should "fail" as they're already deleted
    assert len(result.succeeded) == 0
    assert len(result.failed) == 3


def test_bulk_update_priority(tasks):
    """Test updating priority of multiple nodes."""
    node_ids = [t.id for t in tasks]

    result = bulk_update_priority(node_ids, "high", actor="pm")

    assert len(result.succeeded) == 3
    assert len(result.failed) == 0

    for task_id in node_ids:
        node = get_node(task_id)
        assert node.priority == "high"


def test_bulk_update_priority_invalid(tasks):
    """Test bulk priority update with invalid priority."""
    node_ids = [t.id for t in tasks]

    with pytest.raises(ValidationError):
        bulk_update_priority(node_ids, "super_urgent")


def test_bulk_operations_actor_tracking(project, tasks):
    """Test that bulk operations track the actor correctly."""
    from taskyn.core import list_activity

    node_ids = [t.id for t in tasks]

    # Use reassign which logs activity with actor
    bulk_reassign(node_ids, "developer", actor="scrum_master")

    activity = list_activity(entity_type="node")
    recent_actions = [a for a in activity if a.actor == "scrum_master" and a.action == "assigned"]
    assert len(recent_actions) >= 3


def test_bulk_result_structure():
    """Test BulkResult structure."""
    result = BulkResult(
        succeeded=["id1", "id2"],
        failed=[("id3", "Error message")],
    )

    assert len(result.succeeded) == 2
    assert len(result.failed) == 1
    assert result.failed[0] == ("id3", "Error message")
