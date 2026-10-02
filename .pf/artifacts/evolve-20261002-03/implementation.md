# evolve-20261002-03 Implementation

Timestamp: 2026-10-02T14:54:00Z

## Changed Files

- `src/processforge_core/work_resource_material.py`
- `src/processforge_core/work_resources.py`
- `tools/smoke_work_resource_binding.py`
- `docs/concepts/work-resources.md`
- `docs/ru/concepts/work-resources.md`

## Change Summary

- Added legacy policy canonicalization for Work material indexing, including
  `index_policy: full_text`.
- Updated `grant_rows()` so local-search rows still define the authorized grant
  membership, but resolved resource declarations keep policy precedence for
  Work materialization.
- Added a Work resource binding smoke fixture that covers both legacy
  `full_text` and `fulltext` through registry, selection, snapshot, capsule,
  `work.search` and `work.resolve`.
- Documented the policy precedence for new Work bindings in EN/RU docs.

## Scope Notes

- No immutable capsule, process definition or accepted artifact was rewritten.
- No grants are automatically broadened; selected resource IDs are unchanged.
- `tools/processforge.py` remains out of scope because PF reported an active
  write owner for that file.
- `local_resource_search.py` remains out of scope; existing project indexing
  acceptance smoke still passes.

## Verification Already Run

- `python -X utf8 -m py_compile src/processforge_core/work_resource_material.py src/processforge_core/work_resources.py tools/smoke_work_resource_binding.py tools/smoke_resource_indexing_policy_acceptance.py`
- `python -X utf8 -B tools/smoke_work_resource_binding.py`
- `python -X utf8 -B tools/smoke_resource_indexing_policy_acceptance.py`
- `git diff --check -- src/processforge_core/work_resource_material.py src/processforge_core/work_resources.py tools/smoke_work_resource_binding.py tools/smoke_resource_indexing_policy_acceptance.py docs/concepts/work-resources.md docs/ru/concepts/work-resources.md`
