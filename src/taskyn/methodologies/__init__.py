"""Methodology system for Taskyn."""

from taskyn.methodologies.base import (
    BaseMethodology,
    NodeTypeDefinition,
    EdgeTypeDefinition,
)
from taskyn.methodologies.classic_agile import ClassicAgileMethodology
from taskyn.methodologies.spec_driven import SpecDrivenMethodology
from taskyn.methodologies.learning import LearningMethodology
from taskyn.methodologies.extended_spec import ExtendedSpecMethodology

# Methodology registry
_METHODOLOGIES: dict[str, BaseMethodology] = {}


def _register_methodology(methodology: BaseMethodology) -> None:
    """Register a methodology in the registry."""
    _METHODOLOGIES[methodology.name] = methodology


def get_methodology(name: str) -> BaseMethodology | None:
    """Get a methodology by name."""
    return _METHODOLOGIES.get(name)


def list_methodologies() -> list[BaseMethodology]:
    """List all registered methodologies."""
    return list(_METHODOLOGIES.values())


def methodology_exists(name: str) -> bool:
    """Check if a methodology exists."""
    return name in _METHODOLOGIES


# Register built-in methodologies
_register_methodology(ClassicAgileMethodology())
_register_methodology(SpecDrivenMethodology())
_register_methodology(LearningMethodology())
_register_methodology(ExtendedSpecMethodology())


__all__ = [
    "BaseMethodology",
    "NodeTypeDefinition",
    "EdgeTypeDefinition",
    "get_methodology",
    "list_methodologies",
    "methodology_exists",
]
