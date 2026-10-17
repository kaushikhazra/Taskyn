"""Tests for the extended_spec methodology."""

import pytest

from taskyn.methodologies import get_methodology, methodology_exists
from taskyn.methodologies.extended_spec import ExtendedSpecMethodology


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_extended_spec_registered():
    """extended_spec methodology is registered in the registry."""
    assert methodology_exists("extended_spec")


def test_get_extended_spec_methodology():
    """Can retrieve the extended_spec methodology by name."""
    m = get_methodology("extended_spec")
    assert m is not None
    assert isinstance(m, ExtendedSpecMethodology)
    assert m.name == "extended_spec"
    assert m.display_name == "Extended Spec"


# ---------------------------------------------------------------------------
# Node types
# ---------------------------------------------------------------------------


class TestNodeTypes:
    """Node type definitions."""

    @pytest.fixture()
    def m(self):
        return get_methodology("extended_spec")

    def test_eight_node_types(self, m):
        assert set(m.node_types.keys()) == {
            "research", "plan", "spec",
            "requirement", "design", "dryrun", "implement",
            "todo",
        }

    # All phase nodes share the same status set

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement",
    ])
    def test_phase_node_statuses(self, m, node_type):
        nt = m.node_types[node_type]
        assert nt.valid_statuses == ["draft", "active", "done", "cancelled"]
        assert nt.initial_status == "draft"
        assert nt.terminal_statuses == {"done", "cancelled"}

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement",
    ])
    def test_phase_nodes_no_time_tracking(self, m, node_type):
        assert m.node_types[node_type].can_track_time is False

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement",
    ])
    def test_phase_nodes_not_plannable(self, m, node_type):
        assert m.node_types[node_type].can_be_planned is False

    def test_todo_statuses(self, m):
        nt = m.node_types["todo"]
        assert nt.valid_statuses == ["draft", "active", "done", "cancelled"]
        assert nt.initial_status == "draft"
        assert nt.terminal_statuses == {"done", "cancelled"}

    def test_todo_tracks_time(self, m):
        assert m.node_types["todo"].can_track_time is True

    def test_todo_is_plannable(self, m):
        assert m.node_types["todo"].can_be_planned is True


# ---------------------------------------------------------------------------
# Status transitions — any-to-any
# ---------------------------------------------------------------------------


class TestStatusTransitions:
    """Any valid status can transition to any other valid status."""

    @pytest.fixture()
    def m(self):
        return get_methodology("extended_spec")

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    @pytest.mark.parametrize("from_status,to_status", [
        ("draft", "active"),
        ("draft", "done"),
        ("draft", "cancelled"),
        ("active", "draft"),
        ("active", "done"),
        ("active", "cancelled"),
        ("done", "draft"),
        ("done", "active"),
        ("done", "cancelled"),
        ("cancelled", "draft"),
        ("cancelled", "active"),
        ("cancelled", "done"),
    ])
    def test_any_to_any_transitions(self, m, node_type, from_status, to_status):
        assert m.validate_status_transition(node_type, from_status, to_status)

    def test_invalid_status_rejected(self, m):
        assert not m.validate_status_transition("spec", "draft", "in_progress")

    def test_unknown_node_type_rejected(self, m):
        assert not m.validate_status_transition("epic", "draft", "active")


# ---------------------------------------------------------------------------
# Edge types
# ---------------------------------------------------------------------------


class TestEdgeTypes:
    """Edge type definitions and validation."""

    @pytest.fixture()
    def m(self):
        return get_methodology("extended_spec")

    def test_four_edge_types(self, m):
        assert set(m.edge_types.keys()) == {"parent", "sequence", "depends_on", "blocks"}

    # parent edge

    def test_parent_max_per_source(self, m):
        assert m.edge_types["parent"].max_per_source == 1

    def test_parent_acyclic(self, m):
        assert m.edge_types["parent"].allows_cycles is False

    def test_parent_spec_under_plan(self, m):
        assert len(m.validate_edge("parent", "spec", "plan")) == 0

    @pytest.mark.parametrize("child", ["requirement", "design", "dryrun", "implement"])
    def test_parent_phase_nodes_under_spec(self, m, child):
        assert len(m.validate_edge("parent", child, "spec")) == 0

    @pytest.mark.parametrize("parent_type", [
        "requirement", "design", "dryrun", "implement", "research", "plan",
    ])
    def test_parent_todo_under_any_phase(self, m, parent_type):
        assert len(m.validate_edge("parent", "todo", parent_type)) == 0

    def test_parent_research_has_no_parent(self, m):
        """research is top-level — cannot have a parent."""
        errors = m.validate_edge("parent", "research", "plan")
        assert len(errors) > 0

    def test_parent_plan_has_no_parent(self, m):
        """plan is top-level — cannot have a parent."""
        errors = m.validate_edge("parent", "plan", "research")
        assert len(errors) > 0

    # sequence edge

    def test_sequence_no_cardinality_limit(self, m):
        assert m.edge_types["sequence"].max_per_source is None

    def test_sequence_acyclic(self, m):
        assert m.edge_types["sequence"].allows_cycles is False

    @pytest.mark.parametrize("src,tgt", [
        ("requirement", "design"),
        ("design", "dryrun"),
        ("dryrun", "implement"),
        ("implement", "dryrun"),
        ("research", "spec"),
        ("todo", "todo"),
    ])
    def test_sequence_valid_combinations(self, m, src, tgt):
        assert len(m.validate_edge("sequence", src, tgt)) == 0

    # depends_on and blocks accept all type combinations

    @pytest.mark.parametrize("edge_type", ["depends_on", "blocks"])
    @pytest.mark.parametrize("src", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    @pytest.mark.parametrize("tgt", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    def test_flexible_edges_all_types(self, m, edge_type, src, tgt):
        assert len(m.validate_edge(edge_type, src, tgt)) == 0

    def test_unknown_edge_type_rejected(self, m):
        assert len(m.validate_edge("relates_to", "spec", "spec")) > 0


# ---------------------------------------------------------------------------
# Hierarchy — valid_parent_pairs
# ---------------------------------------------------------------------------


class TestHierarchy:
    """valid_parent_pairs enforcement."""

    @pytest.fixture()
    def m(self):
        return get_methodology("extended_spec")

    def test_spec_parent_must_be_plan(self, m):
        assert m.valid_parent_pairs["spec"] == ["plan"]

    def test_requirement_parent_must_be_spec(self, m):
        assert m.valid_parent_pairs["requirement"] == ["spec"]

    def test_design_parent_must_be_spec(self, m):
        assert m.valid_parent_pairs["design"] == ["spec"]

    def test_dryrun_parent_must_be_spec(self, m):
        assert m.valid_parent_pairs["dryrun"] == ["spec"]

    def test_implement_parent_must_be_spec(self, m):
        assert m.valid_parent_pairs["implement"] == ["spec"]

    def test_todo_parent_options(self, m):
        assert m.valid_parent_pairs["todo"] == [
            "requirement", "design", "dryrun", "implement", "research", "plan",
        ]

    def test_research_is_top_level(self, m):
        assert "research" not in m.valid_parent_pairs

    def test_plan_is_top_level(self, m):
        assert "plan" not in m.valid_parent_pairs

    def test_invalid_parent_pair_rejected(self, m):
        # spec cannot parent under requirement
        errors = m.validate_edge("parent", "spec", "requirement")
        assert len(errors) > 0

    def test_invalid_parent_pair_todo_under_spec(self, m):
        # todo cannot parent directly under spec
        errors = m.validate_edge("parent", "todo", "spec")
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------


class TestHelpers:
    """Methodology helper method overrides."""

    @pytest.fixture()
    def m(self):
        return get_methodology("extended_spec")

    def test_story_type(self, m):
        assert m.get_story_type() == "spec"

    def test_task_type(self, m):
        assert m.get_task_type() == "todo"

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    def test_in_progress_status_is_active(self, m, node_type):
        assert m.get_in_progress_status(node_type) == "active"

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    def test_done_status_is_done(self, m, node_type):
        assert m.get_done_status(node_type) == "done"

    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    def test_blocked_status_is_none(self, m, node_type):
        assert m.get_blocked_status(node_type) is None

    @pytest.mark.parametrize("status", ["done", "cancelled"])
    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    def test_terminal_statuses(self, m, node_type, status):
        assert m.is_terminal_status(node_type, status)

    @pytest.mark.parametrize("status", ["draft", "active"])
    @pytest.mark.parametrize("node_type", [
        "research", "plan", "spec", "requirement", "design", "dryrun", "implement", "todo",
    ])
    def test_non_terminal_statuses(self, m, node_type, status):
        assert not m.is_terminal_status(node_type, status)


# ---------------------------------------------------------------------------
# Sequence edge available in ALL methodologies
# ---------------------------------------------------------------------------


class TestSequenceEdgeUniversal:
    """sequence edge type is available in all four methodologies."""

    @pytest.mark.parametrize("methodology_name", [
        "classic_agile", "spec_driven", "learning", "extended_spec",
    ])
    def test_sequence_edge_registered(self, methodology_name):
        m = get_methodology(methodology_name)
        assert m is not None
        assert "sequence" in m.edge_types

    @pytest.mark.parametrize("methodology_name", [
        "classic_agile", "spec_driven", "learning", "extended_spec",
    ])
    def test_sequence_edge_acyclic(self, methodology_name):
        m = get_methodology(methodology_name)
        assert m.edge_types["sequence"].allows_cycles is False

    @pytest.mark.parametrize("methodology_name", [
        "classic_agile", "spec_driven", "learning", "extended_spec",
    ])
    def test_sequence_edge_no_cardinality_limit(self, methodology_name):
        m = get_methodology(methodology_name)
        assert m.edge_types["sequence"].max_per_source is None
