# Design: extended_spec Methodology

## Node Types

Eight node types, all sharing the same status set.

### Status set (universal across all types)

```
draft → active → done | cancelled
```

- Initial status: `draft`
- Terminal statuses: `done`, `cancelled`
- Any-to-any transitions allowed (no gating)

### Node type table

| Type | Level | can_track_time | can_be_planned | Notes |
|------|-------|----------------|----------------|-------|
| research | top-level | False | False | Freestanding investigation |
| plan | top-level | False | False | Container for specs |
| spec | under plan | False | False | Container for phase nodes |
| requirement | under spec | False | False | What phase |
| design | under spec | False | False | How phase |
| dryrun | under spec | False | False | Review phase (appears twice in chain) |
| implement | under spec | False | False | Build phase |
| todo | leaf | True | True | Atomic work unit |

## Edge Types

### Parent edge

Enforces strict hierarchy via `valid_parent_pairs`.

```
parent:
  source_types: [spec, requirement, design, dryrun, implement, todo]
  target_types: [plan, spec, requirement, design, dryrun, implement, research]
  max_per_source: 1
  allows_cycles: False
```

### Sequence edge (NEW — available to ALL methodologies)

Expresses ordered chains within a spec. Distinct from `depends_on` (cross-spec) and `parent` (containment).

```
sequence:
  source_types: [all node types in the methodology]
  target_types: [all node types in the methodology]
  max_per_source: None  (no limit — one node can sequence to multiple)
  allows_cycles: False
```

For extended_spec, source_types and target_types = all 8 types.

For existing methodologies (classic_agile, spec_driven, learning), sequence is added with all their respective node types in source/target.

### Depends_on edge

Cross-spec or cross-node dependencies.

```
depends_on:
  source_types: [all 8 types]
  target_types: [all 8 types]
  allows_cycles: False
```

### Blocks edge

Blocking relationship.

```
blocks:
  source_types: [all 8 types]
  target_types: [all 8 types]
  allows_cycles: False
```

## Hierarchy (valid_parent_pairs)

```python
{
    "spec":        ["plan"],
    "requirement": ["spec"],
    "design":      ["spec"],
    "dryrun":      ["spec"],
    "implement":   ["spec"],
    "todo":        ["requirement", "design", "dryrun", "implement", "research", "plan"],
}
```

`research` and `plan` have no entry → top-level, no required parent.

## Sequence Chain Pattern

The canonical chain under a spec (connected by `sequence` edges):

```
requirement → design → dryrun → implement → dryrun
```

Both `dryrun` nodes are children of the same `spec` (via `parent` edges). Their position in the chain (design review vs code review) is determined by their sequence context, not their type. This is by design — dryrun is a reusable review phase.

## File Changes

| File | Change |
|------|--------|
| `src/taskyn/db/enums.py` | Add `EXTENDED_SPEC = "extended_spec"` to `Methodology` enum |
| `src/taskyn/methodologies/extended_spec.py` | New file — `ExtendedSpecMethodology` class |
| `src/taskyn/methodologies/__init__.py` | Import and register `ExtendedSpecMethodology` |
| `src/taskyn/methodologies/classic_agile.py` | Add `sequence` edge type |
| `src/taskyn/methodologies/spec_driven.py` | Add `sequence` edge type |
| `src/taskyn/methodologies/learning.py` | Add `sequence` edge type |
| `tests/test_extended_spec_methodology.py` | New test file |

## Helper Method Overrides

```python
get_story_type()  → "spec"
get_task_type()   → "todo"
get_in_progress_status(node_type) → "active" (all types except todo → "in_progress")
get_done_status(node_type)        → "done"
get_blocked_status(node_type)     → None  (no blocked status)
```
