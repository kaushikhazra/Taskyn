"""Tests for methodology system."""

import pytest

from taskyn.methodologies import (
    get_methodology,
    list_methodologies,
    methodology_exists,
)
from taskyn.methodologies.classic_agile import ClassicAgileMethodology


def test_classic_agile_registered():
    """Test that classic_agile methodology is registered."""
    assert methodology_exists("classic_agile")


def test_get_methodology():
    """Test getting a methodology by name."""
    methodology = get_methodology("classic_agile")
    assert methodology is not None
    assert methodology.name == "classic_agile"
    assert methodology.display_name == "Classic Agile"


def test_get_unknown_methodology():
    """Test getting an unknown methodology."""
    methodology = get_methodology("unknown")
    assert methodology is None


def test_list_methodologies():
    """Test listing all methodologies."""
    methodologies = list_methodologies()
    assert len(methodologies) >= 1
    names = [m.name for m in methodologies]
    assert "classic_agile" in names


def test_classic_agile_node_types():
    """Test classic_agile node types."""
    methodology = get_methodology("classic_agile")

    assert "story" in methodology.node_types
    assert "task" in methodology.node_types

    story = methodology.node_types["story"]
    assert story.initial_status == "backlog"
    assert "done" in story.terminal_statuses

    task = methodology.node_types["task"]
    assert task.initial_status == "todo"
    assert "done" in task.terminal_statuses


def test_classic_agile_edge_types():
    """Test classic_agile edge types."""
    methodology = get_methodology("classic_agile")

    assert "parent" in methodology.edge_types
    assert "depends_on" in methodology.edge_types

    parent = methodology.edge_types["parent"]
    assert parent.source_types == ["task", "story"]
    assert parent.target_types == ["story", "epic"]
    assert parent.max_per_source == 1


def test_validate_status_transition():
    """Test status transition validation.

    Any valid status can transition to any other valid status — the methodology
    defines *which* statuses exist, but does not gate movement between them.
    """
    methodology = get_methodology("classic_agile")

    # Forward transitions
    assert methodology.validate_status_transition("task", "todo", "in_progress")
    assert methodology.validate_status_transition("task", "in_progress", "done")
    assert methodology.validate_status_transition("story", "backlog", "ready")

    # Backward / skip transitions — all allowed
    assert methodology.validate_status_transition("task", "todo", "done")
    assert methodology.validate_status_transition("task", "done", "todo")
    assert methodology.validate_status_transition("story", "done", "backlog")

    # Unknown target status still returns False (target must be a valid status)
    assert not methodology.validate_status_transition("task", "todo", "nonexistent")
    # Unknown source status is irrelevant — only the target is checked
    assert methodology.validate_status_transition("task", "nonexistent", "done")


def test_validate_edge():
    """Test edge validation."""
    methodology = get_methodology("classic_agile")

    # Valid edges
    errors = methodology.validate_edge("parent", "task", "story")
    assert len(errors) == 0

    errors = methodology.validate_edge("depends_on", "task", "task")
    assert len(errors) == 0

    # Invalid edges
    errors = methodology.validate_edge("parent", "story", "task")
    assert len(errors) > 0

    errors = methodology.validate_edge("unknown", "task", "story")
    assert len(errors) > 0


def test_helper_methods():
    """Test methodology helper methods."""
    methodology = get_methodology("classic_agile")

    assert methodology.get_story_type() == "story"
    assert methodology.get_task_type() == "task"
    assert methodology.get_in_progress_status("task") == "in_progress"
    assert methodology.get_done_status("task") == "done"
    assert methodology.get_blocked_status("task") == "blocked"
    assert methodology.get_blocked_status("story") is None
