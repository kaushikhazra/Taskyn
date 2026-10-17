"""Validation helpers for graph operations."""

from taskyn.db.models import Node, Edge
from taskyn.methodologies import get_methodology
from taskyn.exceptions import ValidationError


def validate_node_creation(
    project_id: str,
    node_type: str,
    methodology_name: str,
    properties: dict | None = None,
) -> list[str]:
    """
    Validate node creation parameters.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    methodology = get_methodology(methodology_name)
    if methodology is None:
        errors.append(f"Unknown methodology: {methodology_name}")
        return errors

    if not methodology.validate_node_type(node_type):
        valid_types = list(methodology.node_types.keys())
        errors.append(f"Invalid node type '{node_type}' for methodology '{methodology_name}'. Valid types: {valid_types}")
        return errors

    # Validate required properties
    nt = methodology.get_node_type(node_type)
    if nt and properties:
        for prop in nt.required_properties:
            if prop not in properties:
                errors.append(f"Missing required property: {prop}")

    return errors


def validate_node_update(
    node: Node,
    methodology_name: str,
    new_status: str | None = None,
    blocked_reason: str | None = None,
) -> list[str]:
    """
    Validate node update parameters.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    methodology = get_methodology(methodology_name)
    if methodology is None:
        errors.append(f"Unknown methodology: {methodology_name}")
        return errors

    if new_status is not None:
        # Validate status is valid for this node type
        if not methodology.validate_status(node.node_type, new_status):
            nt = methodology.get_node_type(node.node_type)
            valid_statuses = nt.valid_statuses if nt else []
            errors.append(f"Invalid status '{new_status}' for node type '{node.node_type}'. Valid statuses: {valid_statuses}")
            return errors

        # Check blocked status requires reason
        if new_status == "blocked" and not blocked_reason and not node.blocked_reason:
            errors.append("Blocked status requires a blocked_reason")

        # Phase gating: enforce sequential phase flow for spec_driven
        from taskyn.core.cascade import validate_phase_gate
        errors.extend(validate_phase_gate(node.id, node.node_type, node.status, new_status))

    return errors


def validate_status_transition(
    node: Node,
    new_status: str,
    methodology_name: str,
) -> None:
    """
    Validate a status transition, raising an exception if invalid.
    """
    methodology = get_methodology(methodology_name)
    if methodology is None:
        raise ValidationError(f"Unknown methodology: {methodology_name}")

    if not methodology.validate_status(node.node_type, new_status):
        nt = methodology.get_node_type(node.node_type)
        valid_statuses = nt.valid_statuses if nt else []
        raise ValidationError(f"Invalid status '{new_status}' for node type '{node.node_type}'. Valid: {valid_statuses}")



def validate_edge_creation(
    source_node: Node,
    target_node: Node,
    edge_type: str,
    methodology_name: str,
) -> list[str]:
    """
    Validate edge creation parameters.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    methodology = get_methodology(methodology_name)
    if methodology is None:
        errors.append(f"Unknown methodology: {methodology_name}")
        return errors

    # Validate edge type and node type compatibility
    edge_errors = methodology.validate_edge(edge_type, source_node.node_type, target_node.node_type)
    errors.extend(edge_errors)

    return errors
