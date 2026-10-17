"""Tests for learning methodology."""

import pytest

from taskyn.methodologies import get_methodology, methodology_exists
from taskyn.methodologies.learning import LearningMethodology


# --- Registration ---


def test_learning_registered():
    """Learning methodology is registered in the registry."""
    assert methodology_exists("learning")


def test_get_learning_methodology():
    """Can retrieve the learning methodology by name."""
    m = get_methodology("learning")
    assert m is not None
    assert isinstance(m, LearningMethodology)
    assert m.name == "learning"
    assert m.display_name == "Learning"


# --- Node types ---


class TestNodeTypes:
    """Node type definitions."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    def test_three_node_types(self, m):
        assert set(m.node_types.keys()) == {"subject", "topic", "activity"}

    # Subject

    def test_subject_statuses(self, m):
        s = m.node_types["subject"]
        assert s.valid_statuses == ["planned", "active", "completed", "archived"]
        assert s.initial_status == "planned"
        assert s.terminal_statuses == {"completed", "archived"}

    def test_subject_no_time_tracking(self, m):
        assert m.node_types["subject"].can_track_time is False

    def test_subject_has_assignee(self, m):
        assert m.node_types["subject"].can_have_assignee is True

    # Topic

    def test_topic_statuses(self, m):
        t = m.node_types["topic"]
        assert t.valid_statuses == [
            "planned",
            "researching",
            "practicing",
            "documenting",
            "completed",
            "archived",
        ]
        assert t.initial_status == "planned"
        assert t.terminal_statuses == {"completed", "archived"}

    def test_topic_no_time_tracking(self, m):
        assert m.node_types["topic"].can_track_time is False

    # Activity

    def test_activity_statuses(self, m):
        a = m.node_types["activity"]
        assert a.valid_statuses == ["todo", "in_progress", "done", "cancelled"]
        assert a.initial_status == "todo"
        assert a.terminal_statuses == {"done", "cancelled"}

    def test_activity_tracks_time(self, m):
        assert m.node_types["activity"].can_track_time is True


# --- Status transitions ---


class TestSubjectTransitions:
    """Subject status transition validation."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            ("planned", "active"),
            ("planned", "archived"),
            ("active", "completed"),
            ("active", "archived"),
            ("completed", "archived"),
        ],
    )
    def test_valid_transitions(self, m, from_status, to_status):
        assert m.validate_status_transition("subject", from_status, to_status)

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            # Backward / skip transitions — all allowed now
            ("planned", "completed"),
            ("completed", "active"),
            ("archived", "planned"),
            ("archived", "active"),
        ],
    )
    def test_backward_transitions_allowed(self, m, from_status, to_status):
        """Any valid status can transition to any other valid status."""
        assert m.validate_status_transition("subject", from_status, to_status)


class TestTopicTransitions:
    """Topic status transitions — non-gated, flexible phases."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            # From planned — can skip to any phase or complete
            ("planned", "researching"),
            ("planned", "practicing"),
            ("planned", "documenting"),
            ("planned", "completed"),
            ("planned", "archived"),
            # From researching — forward and backward
            ("researching", "practicing"),
            ("researching", "documenting"),
            ("researching", "completed"),
            ("researching", "archived"),
            # From practicing — can revisit researching
            ("practicing", "researching"),
            ("practicing", "documenting"),
            ("practicing", "completed"),
            ("practicing", "archived"),
            # From documenting — can revisit earlier phases
            ("documenting", "researching"),
            ("documenting", "practicing"),
            ("documenting", "completed"),
            ("documenting", "archived"),
            # Terminal
            ("completed", "archived"),
        ],
    )
    def test_valid_transitions(self, m, from_status, to_status):
        assert m.validate_status_transition("topic", from_status, to_status)

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            # Previously "invalid" — all now allowed
            ("completed", "researching"),
            ("completed", "practicing"),
            ("archived", "planned"),
            ("archived", "researching"),
        ],
    )
    def test_backward_transitions_allowed(self, m, from_status, to_status):
        """Any valid status can transition to any other valid status."""
        assert m.validate_status_transition("topic", from_status, to_status)


class TestActivityTransitions:
    """Activity status transitions."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            ("todo", "in_progress"),
            ("todo", "cancelled"),
            ("in_progress", "done"),
            ("in_progress", "cancelled"),
        ],
    )
    def test_valid_transitions(self, m, from_status, to_status):
        assert m.validate_status_transition("activity", from_status, to_status)

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            # Previously "invalid" — all now allowed
            ("todo", "done"),
            ("done", "todo"),
            ("done", "in_progress"),
            ("cancelled", "todo"),
            ("cancelled", "in_progress"),
        ],
    )
    def test_backward_transitions_allowed(self, m, from_status, to_status):
        """Any valid status can transition to any other valid status."""
        assert m.validate_status_transition("activity", from_status, to_status)


# --- Edge types ---


class TestEdgeTypes:
    """Edge type definitions and validation."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    def test_four_edge_types(self, m):
        assert set(m.edge_types.keys()) == {"parent", "sequence", "depends_on", "relates_to"}

    def test_parent_edge(self, m):
        p = m.edge_types["parent"]
        assert p.source_types == ["topic", "activity"]
        assert p.target_types == ["subject", "topic"]
        assert p.max_per_source == 1
        assert p.allows_cycles is False

    def test_depends_on_acyclic(self, m):
        d = m.edge_types["depends_on"]
        assert d.allows_cycles is False

    def test_relates_to_allows_cycles(self, m):
        r = m.edge_types["relates_to"]
        assert r.allows_cycles is True

    # Valid parent edges
    def test_valid_parent_topic_to_subject(self, m):
        assert len(m.validate_edge("parent", "topic", "subject")) == 0

    def test_valid_parent_activity_to_topic(self, m):
        assert len(m.validate_edge("parent", "activity", "topic")) == 0

    # Invalid parent edges
    def test_invalid_parent_subject_to_anything(self, m):
        assert len(m.validate_edge("parent", "subject", "topic")) > 0

    def test_invalid_parent_activity_to_subject(self, m):
        assert len(m.validate_edge("parent", "activity", "subject")) > 0

    # depends_on / relates_to accept any combination
    @pytest.mark.parametrize("edge_type", ["depends_on", "relates_to"])
    @pytest.mark.parametrize("src", ["subject", "topic", "activity"])
    @pytest.mark.parametrize("tgt", ["subject", "topic", "activity"])
    def test_flexible_edges_all_types(self, m, edge_type, src, tgt):
        assert len(m.validate_edge(edge_type, src, tgt)) == 0

    def test_unknown_edge_type(self, m):
        assert len(m.validate_edge("blocks", "topic", "topic")) > 0


# --- Hierarchy ---


class TestHierarchy:
    """valid_parent_pairs enforcement."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    def test_topic_parent_must_be_subject(self, m):
        assert m.valid_parent_pairs["topic"] == ["subject"]

    def test_activity_parent_must_be_topic(self, m):
        assert m.valid_parent_pairs["activity"] == ["topic"]

    def test_subject_has_no_parent(self, m):
        assert "subject" not in m.valid_parent_pairs


# --- Helper methods ---


class TestHelpers:
    """Methodology helper method overrides."""

    @pytest.fixture()
    def m(self):
        return get_methodology("learning")

    def test_story_type(self, m):
        assert m.get_story_type() == "topic"

    def test_task_type(self, m):
        assert m.get_task_type() == "activity"

    # get_in_progress_status varies by node type
    def test_in_progress_activity(self, m):
        assert m.get_in_progress_status("activity") == "in_progress"

    def test_in_progress_topic(self, m):
        assert m.get_in_progress_status("topic") == "researching"

    def test_in_progress_subject(self, m):
        assert m.get_in_progress_status("subject") == "active"

    # get_done_status varies by node type
    def test_done_activity(self, m):
        assert m.get_done_status("activity") == "done"

    def test_done_topic(self, m):
        assert m.get_done_status("topic") == "completed"

    def test_done_subject(self, m):
        assert m.get_done_status("subject") == "completed"

    # No blocked status in learning
    @pytest.mark.parametrize("node_type", ["subject", "topic", "activity"])
    def test_blocked_status_is_none(self, m, node_type):
        assert m.get_blocked_status(node_type) is None

    # Terminal status checks
    @pytest.mark.parametrize("status", ["completed", "archived"])
    def test_subject_terminal(self, m, status):
        assert m.is_terminal_status("subject", status)

    @pytest.mark.parametrize("status", ["completed", "archived"])
    def test_topic_terminal(self, m, status):
        assert m.is_terminal_status("topic", status)

    def test_done_is_terminal_for_activity(self, m):
        assert m.is_terminal_status("activity", "done")

    def test_cancelled_is_terminal_for_activity(self, m):
        assert m.is_terminal_status("activity", "cancelled")

    def test_planned_not_terminal(self, m):
        assert not m.is_terminal_status("subject", "planned")

    def test_researching_not_terminal(self, m):
        assert not m.is_terminal_status("topic", "researching")

    def test_in_progress_not_terminal(self, m):
        assert not m.is_terminal_status("activity", "in_progress")
