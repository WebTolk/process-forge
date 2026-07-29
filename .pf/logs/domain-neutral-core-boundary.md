# Domain-Neutral Core Boundary Log

## 2026-07-29 18:38 +04:00 - primary-agent

Task:
Execute `задания/processforge_domain_neutral_core_boundary_master_prompt.md` as a continuation of the current capability and specialization worktree.

Files changed:
- `.pf/logs/domain-neutral-core-boundary.md`

Artifacts changed:
- None yet.

Templates used:
- `.pf/AGENTS.md` logging format.

Tools used:
- Serena project onboarding and project memories.
- Local memory registry lookup.
- PowerShell repository inventory.

Decisions:
- Treat the dirty capability/specialization changes as required predecessor work and preserve them.
- Use `.pf/AGENTS.md` and `.pf/process-forge.yaml` as the live project process contract because no project-local `.agents/` package exists.
- Keep public core, optional domain examples, and project-local dogfooding as separate ownership layers.

Risks:
- The assignment spans runtime, schemas, processes, prompts, packages, seeds, docs, release tooling, and generated archives.
- Existing uncommitted predecessor changes overlap `tools/processforge.py`, schemas, docs, checksums, and `dist/`.

Next steps:
- Create the assignment execution context and inventory domain assumptions.
- Delegate read-only architecture and test-surface audits with non-overlapping remits.

Handoff:
- Read-only architecture auditor: inspect process, prompt, package, seed, and default-install boundaries.
- Read-only runtime auditor: inspect classifier/detector behavior and schema/registry integration points.
- Read-only assurance auditor: inspect public release manifest, policy, smoke registration, and archive constraints.

## 2026-07-29 18:40 +04:00 - primary-agent

Task:
Create the ProcessForge run, assignment, and immutable assignment capsule.

Files changed:
- `.pf/runs/domain-neutral-core-boundary-20260729/run.yaml`
- `.pf/assignments/task-001-domain-neutral-core-boundary.yaml`

Artifacts changed:
- Assignment capsule pending.

Templates used:
- Built-in `run-create` and `task-create` contracts.

Tools used:
- `python bin/pf.py run-create`
- `python bin/pf.py task-create`
- `python bin/pf.py task-start`
- `python bin/pf.py assignment-capsule`

Decisions:
- Use `multi-agent-task-orchestration` as the neutral governing process.
- Keep all delegated agents read-only; the primary agent is the sole writer for public files.

Risks:
- `task-start` was initially invoked with an obsolete `--run` argument and must be retried with only `--task`.
- PowerShell's default console decoding displayed the Cyrillic required-source path as mojibake; UTF-8 inspection confirmed the file itself is correct.
- Capsule creation was blocked by a stale project snapshot after the prior process-layout migration and by unresolved declared capabilities.

Next steps:
- Refresh the project snapshot, start the task, and retry capsule creation.

Handoff:
- None.

## 2026-07-29 19:52 +04:00 - primary-agent

Task:
Implement and verify the domain-neutral core boundary.

Files changed:
- Runtime/classifier: `tools/processforge.py`, classifier schemas/templates.
- Boundary: `processes/core/`, `prompts/`, `packages/`, `seeds/`,
  `examples/domain-packs/`, policies.
- Assurance: nine domain-neutral smokes, legacy smoke fixtures, validators,
  checksum inventory, release ZIP and manifest.
- Documentation: EN/RU core boundary, classifiers, catalog boundary, workplace
  and context documents.

Artifacts changed:
- `.pf/artifacts/domain-neutral-core-boundary-report.md`
- `.pf/reviews/domain-neutral-core-boundary-review.md`
- `.pf/handoffs/domain-neutral-core-boundary-handoff.md`
- `dist/processforge.zip`
- `dist/processforge.manifest.json`

Tools used:
- Serena for targeted runtime and contract analysis.
- Three read-only subagents: boundary/catalog, classifier/runtime,
  release/assurance.
- ProcessForge schema/public/checksum/release/archive gates.

Decisions:
- Preserve stable ids while moving domain processes into explicit optional
  example packs.
- Keep generic runtime ownership in `process-forge-core`.
- Treat no classifier match as `unclassified`/`unknown`.
- Require explicit registry activation; package presence alone has no effect.
- Preserve useful domain lifecycle tests as optional-pack regressions.

Verification:
- Public release-test PASS: 128/128 checks, 541.148 s.
- Release pack PASS: 762 files.
- Full extracted release-archive-test PASS: 531.57 s.
- No smoke waiver or skipped acceptance gate.

Risks:
- Missing/malformed active classifiers need a dedicated doctor diagnostic.
- Duplicate classifier ids need formal scope precedence.
- Assignment capsule unavailable because the connected workplace does not
  provide `repository_read`, `markdown_editing`, and `schema_validation`.

Next steps:
- Integrate the working tree after review.
- Address classifier diagnostics and workplace capability registry as separate
  follow-up tasks.

Handoff:
- Product result and release archive are ready; see
  `.pf/handoffs/domain-neutral-core-boundary-handoff.md`.
