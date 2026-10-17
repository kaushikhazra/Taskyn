# Task: extended_spec Methodology — Implementation Checklist

_Spec: `.claude/specs/extended-spec-methodology/`_

## Implementation Tasks

- [x] **[Velasari → enums.py]** Add `EXTENDED_SPEC = "extended_spec"` to the `Methodology` enum in `src/taskyn/db/enums.py`
  _requirement: US-5 — methodology registered and discoverable_

- [x] **[Velasari → extended_spec.py]** Create `src/taskyn/methodologies/extended_spec.py` with `ExtendedSpecMethodology` class implementing all 8 node types, 4 edge types (parent, sequence, depends_on, blocks), valid_parent_pairs, and helper method overrides
  _requirement: US-1, US-2, US-3, US-4_

- [x] **[Velasari → __init__.py]** Import `ExtendedSpecMethodology` and call `_register_methodology(ExtendedSpecMethodology())` in `src/taskyn/methodologies/__init__.py`
  _requirement: US-5_

- [x] **[Velasari → classic_agile.py]** Add `sequence` EdgeTypeDefinition to `ClassicAgileMethodology.edge_types` (source/target = epic, story, task; acyclic; no cardinality limit)
  _requirement: US-2_

- [x] **[Velasari → spec_driven.py]** Add `sequence` EdgeTypeDefinition to `SpecDrivenMethodology.edge_types` (source/target = all spec_driven types; acyclic; no cardinality limit)
  _requirement: US-2_

- [x] **[Velasari → learning.py]** Add `sequence` EdgeTypeDefinition to `LearningMethodology.edge_types` (source/target = subject, topic, activity; acyclic; no cardinality limit)
  _requirement: US-2_

- [x] **[Velasari → test_extended_spec_methodology.py]** Write `tests/test_extended_spec_methodology.py` covering: registration, node types (statuses, time tracking, plannability), edge types (parent/sequence/depends_on/blocks), valid_parent_pairs, status transitions (any-to-any), helper methods
  _requirement: US-1, US-2, US-3, US-4, US-5_

- [x] **[Velasari → pytest]** Run `pytest` from `C:\Projects\taskyn` and confirm all tests pass with no regressions
  _requirement: all_
