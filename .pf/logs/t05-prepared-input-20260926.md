# T05 log

## 2026-09-26 08:57 +04:00 - primary
Task: fresh T05 preflight and scope.
Files analyzed: assignment/capsule, T01/T03/T04 contracts, approved T05 card, prepare_worker_run and runtime-driver templates.
Artifacts changed: scope.md, evidence 00-context/00-start.
Templates used: pinned orchestration/intake obligations.
Tools used: actual MCP context/start, scoped source fallback after known Serena limitation.
Decisions: bounded prepared input before one Work/attempt; preserve immutable main context and source/installed boundary. No automatic infrastructure changes.
Risks: current driver preparation/prompt/resource layers may recompute broader workspace state; investigation will trace exact authorization and retry semantics.
Next steps: accept intake, descriptive map/reproduction, domain/architecture before implementation.
Handoff: junior t01_capsule_map owns only worker-driver-map.md; primary owns shared preparation/resource investigation and later integration.

## 2026-09-26 09:20 +04:00 - primary and delegated implementers
Task: implement accepted architecture after actual MCP domain and architecture gates.
Files changed: prepared_input.py, targeted CLI preparation/prompt/collection and Codex input; generic-shell template. Junior wrapper in prepared_executor.py.
Artifacts changed: domain.md and architecture.md frozen through evidence 04/05; before reproduction and source map retained.
Templates used: pinned architecture/implementation obligations.
Tools used: scoped UTF-8 reads, apply_patch, py_compile; Serena Python remains unavailable.
Decisions: immutable attempt manifest and stable receipt IDs; prepared metadata never authorizes an external directory; no worker Work bootstrap. Source current validation still required before launch/collection.
Risks: implementation not yet functionally accepted; compatibility fixtures need updated prepared-input expectations.
Next steps: integrate resource authorization, run developer proof, then independent review/regression and stage acceptance.
Handoff: t01_capsule_map owns wrapper then isolated schema/docs; t02_docs owns only prepared_resources.py. Primary owns shared service/CLI/Codex integration. No parallel writers.

## 2026-09-26 10:06 +04:00 - primary assurance remediation
Task: verify implementation and resolve independent review findings before acceptance.
Files changed: prepared_input/resources, CLI prepared start and collection, worker compatibility tests; schemas/docs delegated separately.
Artifacts changed: developer-proof.py/json, assurance-initial.json, review-initial.md; original failed matrix entry retained (mistyped containment smoke filename, correct test separately PASS).
Templates used: implementation/assurance obligations.
Tools used: isolated source CLI smokes, deterministic offline executor, independent junior review; junior transport 403 interrupted two turns and resumed successfully.
Decisions: ready start consumes exact existing attempt; report preflight precedes atomic receipt publication; governed collection does not complete the primary stage; reject private-path symlinks/junctions; reuse OS-guarded proven-dead-owner lock recovery. Empty read permission denies requested resources.
Risks: source hardening requires new focused and repeated affected tests. Initial schema validation rejected UTF-8 BOM; delegate corrects encoding, no semantic schema exception.
Next steps: independently verify hardening, focused registered regression, final QA then actual stage acceptance and T06.
Handoff: t02_review read-only follow-up; t02_docs focused regression; t01_capsule_map schema/docs final correction. Installed/shared infrastructure untouched.

## 2026-09-26 10:49 +04:00 - primary closeout
Task: accept T05 and continue serial AFK plan.
Files changed: final scoped source hashes in final-checks.json; no installed files.
Artifacts changed: frozen assurance/delivery/evolution reports and actual MCP evidence 07-09; final focused regression, crash/governed and Junction proofs; continuation handoff.
Templates used: pinned assurance/release/evolve obligations.
Tools used: actual MCP transitions, final source QA, run-doctor.
Decisions: source acceptance PASS; actual run_completed and 21 doctor PASS. Legacy capsule unchanged. Scope/report declaration required before worker context creation; ordinary primary Work does not invent permissions.
Risks: hard-link publication support required; direct symlink privilege unavailable. Source acceptance is not installed/new-host proof; no full release gate claimed.
Next steps: T06 integration and actual transport acceptance; preserve failed harness/schema snapshots and all boundaries.
Handoff: .pf/handoffs/t05-prepared-input-20260926.md.
