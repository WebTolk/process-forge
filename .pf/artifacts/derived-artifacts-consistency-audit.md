# Derived Artifacts Consistency Audit

Generated: 2026-08-24 12:00 +04

## Finding

The repository contains historical derived reports that can contradict the
current project snapshot and Runtime state. Current evidence must therefore be
read from fresh commands and current projection files, not old narrative
reports.

Examples observed during this run:

- current project context is fresh at `ctx-20260824-083958-50e142`;
- previous stabilization artifacts explicitly describe earlier stale context
  and residual gaps;
- current Runtime status is stopped, but retains historical PID/endpoint
  fields from 2026-08-14.

## Required Rule

Derived artifacts should carry explicit freshness/source metadata and should be
classified as historical when their source snapshot, runtime generation, or
ledger projection no longer matches current state.

Status: `audit_only_in_this_slice`.
