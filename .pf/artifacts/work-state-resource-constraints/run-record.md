# Run Record: Work State And Resource Constraints

## Objective

Make work state distinguish blocked work from incomplete work, reject unresolved
explicit resource constraints, and prove selected-resource full-text search on
the live Joomla project snapshot.

## Scope

- `src/processforge_core/process_execution.py`
- `tools/processforge.py`
- Resource-selection and process-execution smoke coverage.
- Live snapshot and search verification in the Joomla plugin project.

## Constraints

- An unsatisfied completion requirement is an obligation, not an external
  blocker.
- Explicit version selectors must never fall back to an incompatible resource.
- The Joomla project snapshot remains the authority for selected resources and
  search scope.
