# E01/E02 source implementation report

Status: implementation complete; final assurance and lifecycle closeout in progress.
Baseline: dev at fb3527e4e10ce22b1f7314a6e0e711225327c8d5. No commit created, installed Core unchanged.

## Active Work and scope

Native run `garage-e01-e02-source-implementation-with-approved-explicit-scope-after`, assignment `e01-e02-source-implementation-with-approved-explicit-scope-after-bootstr`; pinned software-feature-development 1.1.0. Immutable capsule SHA256 `ef730f79ece94b1388d0ddc7b619fb051300e90b33f90ca82888ea6b209e9874`. Standard CLI transitions completed orchestration, intake, investigation, domain modeling and architecture. Evidence: active-work.json and commands/*.json. One primary agent, no delegation.

The operator explicitly approved the bounded scope-bootstrap repair outside the blocked lifecycle. It adds creation-only local `work-start --scope-file`, validates complete readiness before capsule publication, retains empty default grants, rejects altered intents on reuse, and binds the exact stopped predecessor and handoff hashes. Other writers still conflict. MCP parameters, old Run/capsule pins and installed Core were not changed. The diagnostic predecessor remains incomplete and stopped; ownership transfer is explicit, not inferred. Historical failure evidence is preserved in implementation-report-bootstrap-blocked.md and commands/diagnostic-orchestration-rejected.json.

## E01

Canonical K is the exact approved draft: 3192 UTF-8 LF bytes, version 1.0.0, SHA256 `81eb72e9447e6a62ea0e9515f6be7a87b592015d06ef68b18ae10fb7e4d86aa6`. Metadata, normalized known-block identity, legacy prefix hashes, deterministic root/hidden rendering and a checked derived template are implemented. Source, schema and Core versions remain separate. Validation is bounded and rejects BOM/CRLF in canonical source, excess size, missing numbered clauses and template drift.

## E02 and R13

Thin `agent-entry plan/check/apply/rollback` CLI delegates to a Core service. Plan/check bypass diagnostic writes and have exact-tree read-only tests. Apply requires the reviewed plan and explicit flag, rechecks targets/source/budget inputs, and refuses ownership, encoding, permissions, path and budget conflicts. Public plans expose generated text and hashes/offsets without user text or absolute paths. Root user bytes and known hidden extended sections are preserved.

Transactions use an OS-held lock, private preimages, bounded integrity-checked journals, atomic per-file data replacement and manifest-last order. Windows ACL inheritance is preflighted on empty isolated files; data and owner/group/DACL restoration are separate journaled steps. Recovery is explicit rollback; late user edits block all restoration. No multi-file atomicity, adversarial-owner sandbox or automatic forward recovery is claimed. Private scratch/journals are retained recovery evidence.

Budget observations distinguish canonical K, placed K, whole files and ordered/duplicated selections. Byte, Unicode-scalar and UTF-16-unit accounting are distinct. Known loss of any required text blocks apply. Warnings remain warnings; unknown/token/default observations never become client readiness. Client discovery/import expansion and host configuration belong to E05/E10, not this generic raw-concatenation service.

## Source files

- `src/processforge_core/agent_entry.py`
- `src/processforge_core/agent_entry_migration.py`
- `templates/agent-entry-contract.md`
- `templates/agent-entry-contract.json`
- `templates/project-agents-template.md`
- `schemas/agent-entry.schema.json`
- `tools/processforge.py`
- `tools/smoke_agent_entry.py`
- `docs/concepts/agent-entry.md`
- `docs/ru/concepts/agent-entry.md`
- `checksums/processforge.sha256`
- `src/processforge_core/process_execution.py`
- `tools/smoke_work_start_scope.py`
- `docs/concepts/work-context.md`
- `docs/ru/concepts/work-context.md`

## Compatibility and residual scope

Current root AGENTS.md remains absent; .pf/AGENTS.md, START, snapshot and all earlier capsules/planning artifacts remain unchanged. No migration of this project, archive creation, Core installation, host restart/reconnect or publication. E03 onward remains pending. The existing integrity smoke has an identical failure on pristine HEAD (baseline-integrity.json); it expects an older reason code for a corrupt context. The broad live schema scan initially found an unrelated empty hook outbox payload. Neither was silently repaired. Final results and review are in assurance.md.

## Implementation decisions and evidence

Existing local documentation has no applicable Win32 reference. Official [ReplaceFileW documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew) was retrieved directly after the web-search transport timed out. Local Windows probes established an ACL inheritance difference and drove explicit preflight/restoration/crash tests. This does not certify every filesystem or ACL arrangement; unsupported preservation fails closed.

Persistent evidence: commands/ receipts, preservation.json, design.md, work-scope.json; isolated pristine baseline and public-source qualification trees under .pf/tmp are retained to reproduce the two pre-existing/environment boundaries. User-owned changes and old research are preserved.
