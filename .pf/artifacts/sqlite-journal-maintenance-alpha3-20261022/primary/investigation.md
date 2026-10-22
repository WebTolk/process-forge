# Existing behavior and required maintenance additions

The existing explicit migration entry tools/migrate-hook-journals.py already
streams legacy events/raw rows, validates stable native identities, detects ID
conflicts in a bounded temporary SQLite index, marks both destination owners
importing, imports idempotently and finishes only after source checks and
integrity/count validation. Original files remain intact. Existing Core owners:
ProcessEventJournal, RawHookJournal, sqlite_storage transaction/database helpers.
Accounting storage already uses SQLite backup rather than live file copies.

Missing parts for the chosen task: consistent verified backup bundles, exact raw
corruption quarantine with offset/hash/source metadata, integrated pre-import
backups and post-import evidence, and safe explicit restore. Diagnostics alone
currently discard invalid row bytes from the report and lack a quarantine artifact.
The migration script imports Main unnecessarily for unused code and locates real
logic at a tool boundary. Move that owning logic into maintenance services and
keep the released explicit script as a thin compatible entrypoint.

Source scope checks found unrelated OOP54–55 changes in Main/resources and an
untracked platform owner. They are preserved and excluded from release commits.
The new feature is an additive operator CLI over shared library services; no MCP,
Runtime routing, active project grants or file-only requirements are altered.
Raw identity primitives currently live in a pure provider-neutral module under
pf_runtime; access them through an explicit narrow validator dependency/default
adapter, without importing Host, Runtime or Main. No new native identity algorithm.
