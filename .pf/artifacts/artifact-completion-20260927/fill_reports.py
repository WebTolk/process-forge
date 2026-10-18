from work import *
from inventory import TARGETS

REPORTS = {
'project-profile.md': '''# Project Profile

## Status and purpose

Reviewed from project source and delivery evidence on 2026-09-27. ProcessForge
is a file-first framework for defining, versioning and executing governed work.
Assignments, immutable execution contexts, artifacts, gates and handoffs make
work reproducible across executor providers. Runtime, MCP and provider adapters
extend the file model; they are not prerequisites for Garage/file-only work.

## Identity and implementation

- Project id: `process-forge`; manifest type: `processforge-development`.
- Current classifier type: `software.python`; this describes the implementation,
  not a mandatory platform overlay.
- Product version: `1.1.0`. Exact accepted installed build: `ddff5983`.
- Implementation: Python; process/package/config data: YAML and JSON; schemas:
  JSON Schema; documentation: Markdown. Runtime dependency: `PyYAML>=6.0`.
- Python 3.11+ is recommended by the project README. No platform or toolchain
  overlay is selected in the current project context.
- Default project process: `software-feature-development@1.1.0`.

## Layers and present behavior

Core owns context/pinning, lifecycle, authorization, evidence and durable events.
Official processes/packages are extension data under `packs/official/`.
Workplace configuration is separate from project state. Provider adapters and
MCP are integration boundaries. See [repository map](repository-map.md).

The T01-T10 delivery includes Work contracts, authorized resource access,
normalized context, provider adapters, prepared immutable input, integrated
acceptance, optional diagnostics, a local monitor and the T07 egress engine.
The qualified strict-egress route is managed HTTP/JSON on Windows. Native Codex,
generic-shell and isolated-local strict egress remain unsupported. A prior
installed-process test is not proof that a connected application MCP reloaded.

## Ownership, privacy and work entry

Use `.pf/AGENTS.md`, current context and the selected assignment/capsule. One
writer owns each file scope. Approved artifacts and recorded capsules are
protected. Public distribution files must not contain machine paths or secrets;
`.pf` evidence, Runtime state, private local configuration, archives and backups
have separate delivery/privacy boundaries. Retain declared durable evidence.

Start with the [artifact index](README.md), [conventions](project-conventions.md)
and [verified delivery](t07-engine-20260926/final/closeout.md).

## Evidence

[Product README](../../README.md), [dependencies](../../requirements.txt),
[project manifest](../process-forge.yaml),
[delivery report](t07-engine-20260926/final/delivery.md),
[current coverage](artifact-completion-20260927/coverage.md).
''',
'repository-map.md': '''# Repository Map

Reviewed on 2026-09-27. This is a maintained responsibility map, not a recursive
listing of historical temporary files. Paths below are relative to the repo.

## Runtime implementation

| Path | Responsibility |
| --- | --- |
| `bin/pf.py` | Public CLI launcher |
| `tools/processforge.py` | Command registration and orchestration |
| `src/processforge_core/bootstrap.py` | Core bootstrap |
| `src/processforge_core/garage.py` | File-first Garage operations |
| `src/processforge_core/process_execution.py` | Pinned process execution and transitions |
| `src/processforge_core/work_context.py` | Work execution contexts/contracts |
| `src/processforge_core/work_resources.py` | Work resource authorization |
| `src/processforge_core/work_resource_material.py` | Bounded authorized material |
| `src/processforge_core/prepared_input.py` | Prepared immutable executor input |
| `src/processforge_core/egress/` | Policy, classification, views, storage, broker and transport |
| `src/processforge_core/core_update.py` | Manifest-controlled Core updates |
| `src/processforge_core/diagnostics.py` | Optional diagnostics |
| `src/processforge_core/runtime_metrics.py` | Bounded local activity metrics |
| `src/processforge_core/host_integration.py` | Host integration boundary |
| `src/processforge_core/local_resource_search.py` | Local resource search |
| `src/processforge_core/process_catalog/` | Process catalog |
| `src/processforge_core/common/` | Shared Core helpers |

## Product data and validation

| Path | Responsibility |
| --- | --- |
| `packs/official/` | Bundled domain processes and packages |
| `processes/` | Core/custom process definitions and companions |
| `packages/` | Knowledge/package manifests |
| `schemas/` | JSON Schema contracts |
| `templates/` | Assignment, artifact, review, handoff and other templates |
| `docs/`, `docs/ru/` | English/Russian documentation |
| `prompts/`, `examples/`, `seeds/` | Agent entry points and reusable examples |
| `tools/smoke_*.py` | Behavioral smoke/regression checks |
| `tools/validate-*.py` | Schemas, checksums and public-cleanliness checks |
| `checksums/` | Public checksum inventory |
| `dist/`, `updates/` | Distribution/update artifacts and metadata |

## Project-local process state

`.pf/AGENTS.md` and `.pf/process-forge.yaml` are the entry points. Assignments and
runs live under `.pf/assignments/` and `.pf/runs/`. Immutable assignment capsules
live under `.pf/contexts/assignment-capsules/`. Artifacts, reviews, ADRs, logs and
handoffs have separate directories. `.pf/runtime/` contains derived operational
state. Temporary work belongs under `.pf/tmp/`; declared durable evidence there
is retained. No project-local `.agents` flow package was present at this review.

Current navigation: [artifact index](README.md),
[coverage matrix](artifact-completion-20260927/coverage.md),
[egress design](../../docs/concepts/egress-engine.md),
[Work context](../../docs/concepts/work-context.md),
[Runtime monitor](../../docs/concepts/runtime-monitor.md).
''',
'project-conventions.md': '''# Project Conventions

Confirmed from `.pf/AGENTS.md`, the pinned process, existing modules, templates
and delivery evidence on 2026-09-27. These observations do not introduce a new
global platform/toolchain policy.

## Work and ownership

Read current context before work. Start/resume the governed Work, read its
assignment and immutable capsule, then use standard transitions with evidence.
ProcessForge chooses stages. Do not hand-edit lifecycle YAML, rewrite capsules,
silently skip optional stages or overwrite approved evidence. Keep unrelated
dirty work intact. The current pinned process permits one primary agent and no
subagents.

## Names, code and data

Use stable lowercase machine ids, consistent with existing process/artifact ids.
Python modules/functions follow existing snake_case names; preserve established
module boundaries and local style. Use UTF-8 text and explicit serialization.
Schema, YAML/JSON configuration and Python validation must agree. Domain-specific
rules belong in extension packages rather than hardcoded Core branches.

## Artifacts and review

Use [artifact-template](../../templates/artifact-template.md),
[review-template](../../templates/review-template.md) and
[handoff-template](../../templates/handoff-template.md). Record objective,
scope, inputs, changes, evidence, status and residual limits. Use append-only
logs. Distinguish current knowledge from historical proof. A `path_hint` is not
a mandatory filename. Do not mark a human approval when only self-review ran.
On Windows use `work-transition --evidence-file` for structured evidence.
Use UTF-8 file writes; the default PowerShell text-to-native pipe may be ASCII.

## Verification and delivery

Run checks relevant to the changed behavior. Existing Python checks live in
`tools/smoke_*.py` and `tools/validate-*.py`. Public changes require the project
schema/checksum/cleanliness gates; do not add unrelated test suites to a local
documentation-only task. Record actual commands and results.

Core delivery uses a qualified clean candidate, `release-pack`, consumer archive
validation, then `core-update plan/apply/status` when installation is authorized.
Preserve manifests and automatic backups. Source, archive, installed process and
connected host/MCP acceptance are distinct. Do not reinstall for private `.pf`
documentation changes. Runtime or host lifecycle actions require their own
applicable authorization.

## Documentation and privacy

Public behavior docs have English/Russian counterparts where the project uses
them. Keep public files free of secrets and machine-specific paths. Use local
documentation first. Record unavailable checks honestly. Temporary directories
belong under `.pf/tmp/`; protected historical evidence is never casual cleanup.

Sources: [project instructions](../AGENTS.md),
[pinned process source](../../packs/official/software-development/processes/software-feature-development.yaml),
[delivery](t07-engine-20260926/final/delivery.md).
''',
'toolchain-detection-report.md': '''# Toolchain Detection Report

Observation date: 2026-09-27. No toolchain overlay is selected in the current
context. Python is an observed implementation/runtime requirement, not an
implicitly selected global contract.

## Project tools

| Tool | Evidence and use |
| --- | --- |
| Python + PyYAML | `requirements.txt`; installed PF CLI and YAML inventory ran |
| `bin/pf.py` | Standard CLI launcher; work state/transitions and diagnostics |
| `tools/validate-process-forge-schemas.py` | Project schema validation |
| `tools/validate-process-forge-checksums.py` | Public checksum inventory |
| `tools/validate-public-cleanliness.py` | Public distribution privacy checks |
| `tools/smoke_*.py` | Existing behavioral regression checks |
| Git | Source identity, diff inspection and clean release candidate |
| OpenSSL | T07 installed qualification uses TLS fixtures; prior delivery evidence |

Python 3.11+ is recommended by the [product README](../../README.md).
No PHP/frontend tooling is required by this documentation task.

## Capability decisions

The manifest requires repository_read, markdown_editing and schema_validation.
It optionally declares repository_symbol_analysis, official_documentation_lookup
and browser_verification. The pinned software process adds repository_write,
test_running, review and stage-specific coordination/architecture roles.

Serena pattern search is available; Python symbol analysis is not configured.
For this task, structured Python/PyYAML inventory and direct bounded file reads
are the documented fallback. Native filesystem editing and the installed PF CLI
work. No new global tool installation or capability waiver is needed.

## Validation boundary

This task runs artifact/reference/preservation checks and PF doctors. It does
not repeat prior feature suites or claim browser/TLS testing occurred anew.
See the [current test report](artifact-completion-20260927/test-report.md) and
[prior installed acceptance](t07-engine-20260926/final/delivery.md).
''',
'mcp-capability-report.md': '''# MCP Capability Report

Observed on 2026-09-27; registration, availability and operation success are
different facts.

| Provider/capability | Observation | Current decision |
| --- | --- | --- |
| ProcessForge `pf.context` | Tool exposed; call timed out after 60 seconds | Standard installed PF CLI fallback |
| ProcessForge Work lifecycle | CLI work-start/work-state/work-transition operational | Continue governed file-first work |
| Serena pattern search | Successfully read project instructions and reports | Use for bounded repository/document analysis |
| Serena Python symbols | Active project has no configured language | Python/YAML inventory fallback; no symbol-analysis claim |
| Browser verification | No web UI changed in this task | not_applicable |

No MCP provider is made mandatory merely because it is installed. Current
project context is fresh and execution-ready through the standard fallback.
No Runtime/MCP/hook/Ledger start, restart, repair or configuration write is part
of this artifact task. Connected host reload remains unverified.

Evidence: [task context](artifact-completion-20260927/execution-context-summary-r02.md),
[verification report](artifact-completion-20260927/test-report.md),
[earlier live check](../logs/delivery-recheck-20260927T0348Z.md).
''',
'template-matching-report.md': '''# Template Matching Report

Reviewed on 2026-09-27 against the pinned software-feature-development process.

| Required template | Repository source | Application |
| --- | --- | --- |
| assignment-template | `templates/assignment-template.md` | Standard Work CLI generates assignment state |
| artifact-template | `templates/artifact-template.md` | Metadata, summary, content and review in all 29 current artifacts |
| review-template | `templates/review-template.md` | New artifact-completion review |
| handoff-template | `templates/handoff-template.md` | New task completion handoff |

The flow manifest maps templates to the distribution `templates/` directory.
The project `.pf/templates/` contains no local override files at this review.
Project profile, conventions and map follow the corresponding template purpose,
with actual source-backed content replacing generated detection placeholders.

Adaptation: body checksums in the new artifact bundle have explicit
`content_section_utf8_lf` scope to avoid a recursive whole-file hash. PF records
whole-file hashes separately when evidence is submitted. Self-review is labelled
as such; no human approval is invented. Optional outputs state applicability and
the reason instead of leaving template tokens or empty headings.

Do not use domain templates as a substitute for the pinned process. Global
legacy development-flow skills, Joomla overlays and unrelated artifact-template
creation workflows are not required here.

Sources: [artifact template](../../templates/artifact-template.md),
[process](../../packs/official/software-development/processes/software-feature-development.yaml),
[current artifact index](artifact-completion-20260927/README.md).
''',
'global-resource-matching-report.md': '''# Resource Matching Report

Reviewed on 2026-09-27. This report describes declared and selected resources;
it does not expand filesystem access or assert all global resources were loaded.

## Selected Work resources

| Resource id | Meaning | Selection |
| --- | --- | --- |
| `project.process-forge:project-profile` | Project profile note | Selected by the current capsule |
| `project.process-forge:project-artifacts` | Project artifact reference collection | Selected by the current capsule |

The project package declares these resources in
[project.process-forge.yaml](../packages/project.process-forge.yaml). Profile
loads when relevant with full-text indexing; artifact collection loads on demand
with metadata indexing. Resource presence is not permission to publish its
contents or bypass Work scope.

## Packages, platform and tools

The manifest knowledge stack includes `processforge.core` from the distribution
and `project.process-forge` from the project. The pinned software process requires
`process-forge-core` and `processforge.official.software-development`.
No platform/toolchain overlay or active specialization is selected. This does
not imply Python is absent: it is the observed implementation language.

Required process templates are documented in the
[template report](template-matching-report.md). Actual tools and MCP limitations
are documented in the [tool report](toolchain-detection-report.md) and
[MCP report](mcp-capability-report.md).

## Readiness and limits

Standard context check reported fresh resources and ready execution with no
missing required capabilities. The connected MCP timed out; no waiver or global
registration is inferred from that observation. Current Work uses installed CLI
and directly verified local tools. Broader global docs/skills/platform roots are
not imported into the project package by this task.
''',
'README.md': '''# ProcessForge project artifacts

Start here for the current project knowledge and delivery evidence. Updated on
2026-09-27 by the governed artifact-completion Work.

## Current project knowledge

- [Project profile](project-profile.md): purpose, layers and supported behavior.
- [Repository map](repository-map.md): code, product data and private process state.
- [Project conventions](project-conventions.md): ownership, evidence and delivery.
- [Tools](toolchain-detection-report.md), [MCP](mcp-capability-report.md),
  [templates](template-matching-report.md), [resource selection](global-resource-matching-report.md).

## Required artifact completeness

- [Complete artifact set for this Work](artifact-completion-20260927/README.md):
  all 29 artifact definitions, with explicit applicability decisions.
- [T01-T10 coverage matrix](artifact-completion-20260927/coverage.md):
  340 mandatory artifact-ID bindings across 17 completed delivery works.
- [Machine-readable evidence](artifact-completion-20260927/coverage.json):
  exact assignment paths, hashes and historical reference findings.
- [Verification](artifact-completion-20260927/test-report.md) and
  [documentation handoff](../handoffs/artifact-completion-20260927.md).

## Accepted implementation delivery

[T07 final delivery](t07-engine-20260926/final/delivery.md) and
[closeout](t07-engine-20260926/final/closeout.md) identify installed build
`ddff5983`, the standard Core update, 1015 verified owned files and the recorded
53-check installed qualification. [T10 closeout](t10-operator-runtime-fix-20260926/closeout.md)
records completion of the local operator/monitor work. Full per-task evidence,
including T01-T09, is linked from the coverage matrix.

The qualified strict-egress route is managed HTTP/JSON on Windows. Native and
isolated-local strict routes remain unsupported. Connected host MCP reload is
not established by installed CLI tests. These boundaries are part of acceptance.

## Historical material

Older bootstrap reports, generated onboarding/classification reports, proposals,
reviews and run summaries retain their original date and meaning. Root files
such as `changed-files.md` and `consolidated-roadmap.md` describe bootstrap work;
they are not current delivery summaries. Hash-recorded evidence and capsules
must not be rewritten to make a new report appear complete.

New artifacts follow [artifact-template](../../templates/artifact-template.md).
Use current context/Work state for lifecycle truth; this index is navigation.
'''
}

def main():
    assert set(REPORTS)==set(TARGETS)
    assert state('implementation-edit-state')['stage']['id']=='implementation'
    baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
    for name,body in REPORTS.items():
        p=ROOT/'.pf/artifacts'/name
        assert sha(p)==baseline['target_sha256'][name], name
        p.write_text(body,encoding='utf-8',newline='\n')
    doc('changed-files','Changed documentation files', '\n'.join('- `.pf/artifacts/'+n+'`: filled current project documentation; original in `before/'+n+'`.' for n in TARGETS)+'''

New files: this artifact-completion-20260927 bundle (29 effective typed artifacts, coverage/index, audit helpers, preservation baseline, command evidence and original-report copies); .pf/logs/artifact-completion-20260927.md; the task-specific review and handoff. PF CLI owns generated assignment/run/context records. Source, installed Core and historical stage evidence are outside this change.''',role='developer')
    doc('change-summary','Artifact completion changes', '''Replaced eight generated/observed navigation reports with reviewed, source-backed content. The project profile now states purpose and Python implementation; the map explains actual modules; conventions describe ownership, artifacts, review and standard updater delivery. Tool/MCP/template/resource reports distinguish actual observations from configured contracts and unavailable checks.

Added a complete artifact index for this Work and a per-work evidence map for all 17 current delivery runs. Coverage verifies all 340 required ID bindings. Original report bytes, protected evidence and source hashes are retained for comparison. New documents are self-reviewed and ready_for_review; this does not assert human approval.

No runtime behavior, package, installed Core, registry, capsule or old run status was changed. Older hash differences are explicitly recorded rather than fixed by rewriting history. Readable r02 orchestration documents supersede the first encoding-damaged capture and are attached through normal evidence.''',role='developer')
    log('Fill project reports','Eight root reports and implementation artifacts','Written with UTF-8; originals retained','Validate complete index and artifacts before assurance')

if __name__=='__main__': main()
