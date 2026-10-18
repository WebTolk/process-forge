# evolve-20261002-03 Evolution Report

Timestamp: 2026-10-02T15:06:00Z

## Captured Evolution

Work resource materialization now treats resolved resource declarations as the
authoritative source for explicit `indexing` and recognized legacy
`index_policy` values. This prevents generated metadata-only local-search rows
from downgrading legacy full-text documentation during new Work binding
creation.

## Follow-Up Knowledge

- Keep distinguishing grant membership from materialization policy.
- When local-search rows are generated from project snapshots, do not assume
  their `indexing` value is the original declaration.
- For future project-search parity work, inspect `tools/processforge.py` once
  its active owner releases the file.

## No Instruction Update

No global instruction or skill update is proposed. This is a project-local
implementation rule captured in source, tests, docs and the task handoff.
