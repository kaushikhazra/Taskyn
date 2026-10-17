# Requirement: extended_spec Methodology

## Overview

Taskyn needs a new `extended_spec` methodology that models the full spec-enhanced development lifecycle — from initial research through planning, specification, implementation, and review. This methodology reflects how Kaushik actually works in practice with the Velasari system.

## User Stories

### US-1: Full lifecycle node types

**As a** developer using Taskyn,  
**I want** node types that mirror the full spec-driven workflow (research → plan → spec → requirement → design → dryrun → implement → todo),  
**So that** I can track work at each distinct phase of the development lifecycle without forcing everything into generic buckets.

**Acceptance criteria:**
- Node types: `research`, `plan`, `spec`, `requirement`, `design`, `dryrun`, `implement`, `todo`
- All node types accept statuses: `draft`, `active`, `done`, `cancelled`
- `research` and `plan` are top-level (no required parent)
- `spec` must parent under `plan`
- `requirement`, `design`, `dryrun`, `implement` must parent under `spec`
- `todo` can parent under any of: `requirement`, `design`, `dryrun`, `implement`, `research`, `plan`

### US-2: Sequence edges for chain ordering

**As a** developer,  
**I want** a `sequence` edge type to express ordered chains within a spec (e.g. requirement → design → dryrun → implement → dryrun),  
**So that** the process chain is explicit in the graph without conflating it with cross-spec dependencies (`depends_on`).

**Acceptance criteria:**
- A new `sequence` edge type is available
- `sequence` edges are available in ALL methodologies (classic_agile, spec_driven, learning, extended_spec)
- `sequence` edges are acyclic (the chain has a direction)
- `sequence` edges have no cardinality limit (a node can sequence to multiple things)

### US-3: Todo as the only plannable unit

**As a** developer,  
**I want** only `todo` nodes to be plannable and time-trackable,  
**So that** daily plans contain concrete atomic work items, not high-level phase containers.

**Acceptance criteria:**
- `todo` nodes: `can_be_planned=True`, `can_track_time=True`
- All other node types: `can_be_planned=False`, `can_track_time=False`

### US-4: Any-to-any status transitions

**As a** developer,  
**I want** to move nodes between any valid statuses freely (no gating),  
**So that** I can reopen, rollback, or correct status without fighting the system.

**Acceptance criteria:**
- Any valid status can transition to any other valid status for the same node type
- `allowed_transitions` is retained for documentation only

### US-5: Methodology registered and discoverable

**As a** developer or AI agent,  
**I want** the `extended_spec` methodology to be registered in the Taskyn registry,  
**So that** projects can use it and `pm_get_methodology_info` returns its structure.

**Acceptance criteria:**
- `methodology_exists("extended_spec")` returns `True`
- `get_methodology("extended_spec")` returns an `ExtendedSpecMethodology` instance
- The methodology enum in `enums.py` includes `EXTENDED_SPEC = "extended_spec"`
