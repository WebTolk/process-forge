# Sequential classifier and artifact policies

Date: 2026-10-18. Baseline: c75797d9a2d206c3ce5b3b6c5968fed092cbcd1e.
ParameterMergePolicy is delivered to both dev remotes and all six preceding Works
are terminal. The primary reread the original specs/ADR/domain/direction and the
10 October migration contract after that major task. The current source context
is fresh/ready; use existing source CLI, not the known stale installed MCP view.
Latest user instructions authorize autonomous sequential refactoring until 09:00
device time on 19 October (UTC+04), then finishing in-flight tasks and a night report.
They supersede historical stop/no-implementation paragraphs in old planning documents.

This bounded cycle contains TWO SMALL ORDERED transfers with separate Core owners,
one writer of the monolith, one final documentation/assurance/delivery cycle, and
no new functionality. It does not close the original OOP epics. MCP resource features,
new frameworks, container/provider systems, installation and Runtime work are excluded.

## 1. Classifier matching

Owner: ProjectClassifierRulePolicy in processforge_core.project.classification.
Public ordinary instance method: matches(rule, available_paths) -> bool.
Its existing condition algorithm is private _condition_matches(condition, available_paths).
Move the exact path_matches_pattern(path, pattern) primitive into existing common.paths,
which is shared by classifier and other detection responsibilities. Keep rel unchanged.

Preserve the exact when/all/any checks: an all LIST takes precedence even when empty;
nonempty all uses short circuit, any uses short circuit, wrong shapes return False.
Condition exists must be a nonblank string; strip and normalize backslashes as before.
The shared primitive normalizes the path, tries fnmatch.fnmatch on full path then
Path(normalized).name. Preserve platform normalization and basename behavior; no
fnmatchcase, casefold, PurePosixPath or new input normalization/validation.

Migrate BOTH rule callers: inactive_official_classifier_hints and classify_project.
Other matcher consumers detection_group_matches and platform_detection_matches
directly import the common primitive. Delete all three old monolith definitions;
the canonical common matcher name intentionally remains in imports and call sites.
Classifier registry/activation and tree traversal remain in their existing owners.

## 2. Process artifact declarations

Owner: ProcessArtifactDeclarationPolicy in processforge_core.process_catalog.artifacts.
Public ordinary instance methods: defined_ids(process), declared_ids(process),
produced_ids(process), returning the same sets as the three existing algorithms.
Move artifact_definition_ids, declared_process_artifact_ids and
produced_process_artifact_ids; remove the three old definitions and migrate every
authoring, process-validation and builtin-catalogue caller to the actual owner.

Preserve dict/list distinctions, truthiness of IDs, duplicate handling, str conversion
and exception order. The effective LATE monolith as_list returns a list unchanged and
[] for ANY non-list. process_catalog.service._as_list has different scalar semantics
and must not be reused. string_list preserves the existing list conversion/filter
call order and comma-separated string behavior. Small private value-shaping helpers
may stay with this owner; the generic monolith helpers remain for their other actual
consumers. No callback or import to the monolith, and no new coercion/error handling.
Full validators, companion-file reading, catalogue registration and activation remain
outside this pure declaration responsibility.

## Concrete ownership and sequence

The primary owns only its artifacts, night log, handoff and scratch.
Core worker owns classification.py, common/paths.py and process_catalog/artifacts.py.
It implements classifier/matcher first, artifact declarations second, then stops.
The consumer worker subsequently owns only tools/processforge.py and migrates the
same two groups in order. It starts after Core is complete, so CLI imports stay usable.
Docs owns the two current EN/RU Core structure references and checksum inventory.
QA owns only its reports and scratch. Independent reviewer starts after code, docs
and focused QA, with a fresh native context and read-only product scope.

Exact product paths, seven total:

- src/processforge_core/project/classification.py
- src/processforge_core/common/paths.py
- src/processforge_core/process_catalog/artifacts.py
- tools/processforge.py
- docs/concepts/python-core-structure.md
- docs/ru/concepts/python-core-structure.md
- checksums/processforge.sha256

One writer per file. No worker mutates Git, contacts remotes, changes infrastructure,
starts nested agents, rebuilds capsules or performs lifecycle transitions. Read-only
local Git inspection is allowed on the relevant source paths. Use exact Work selectors
and validate the immutable capsule. Source-only Serena symbol mapping already located
the helpers; stalled monolith reference queries were replaced by bounded rg/AST.
Use Serena where available; avoid broad scans of archives or unrelated temporary trees.

Reasoning effort follows the user's latest instruction: Core high, consumer medium,
docs medium, QA high, independent review high. Native model stays gpt-6.1-sol.
Use bounded source reads and small implementation checks, not broad test infrastructure.

## Assurance and delivery

baseline-functions.json freezes all eight relevant old helpers before changes,
including the effective last as_list definition and original common.paths source.
The primary runs only the affected existing smoke scripts in its own short .pf/tmp
fixtures after code completion; native worker temporary fixtures are known to be
permission-blocked and must not be retried or repaired. QA reads that immutable
receipt, performs a small meaningful parity corpus for both groups and direct/copied
Core isolation, and records matching source hashes. No permanent new test suite.

Focused existing smokes: project classification, classifier inventory pruning, official
pack classifier data, no-hardcoded-file project detection, builtin process catalogue,
process stage contract normalization and process definition schema contract. These
exercise the actual changed rule/caller paths. Do not run unrelated release/archive
suites or global inventory validation; update only affected inventory rows with the
existing released_content/sha256 helper. Preserve the three known unrelated drifts.
ZIP-content checks after packaging are temporarily excluded by direct user instruction.

Architecture acceptance touches D01/D02/D06/D09/D11 through common Core ownership and
consumer migration. D03/D04/D05/D08/D10 gain no new mechanisms or lifetimes. D07 and
R01-R12 retain identity, access, live reads, guard/error order, unknown fields, journals,
locks, recovery, one-writer rules and private-path boundaries: these pure policies
introduce no I/O, caching, permission decisions, lifecycle authority or transport APIs.
Standard modules, ordinary stateless objects and explicit owning imports are sufficient.

After completed implementation: focused evidence, independent clean-context review,
resolve blocking findings, separate commit and same-SHA push/readback on both dev
remotes. GitVerse uses existing GITVERSE_TOKEN through process-only authorization.
No archive/install/Runtime/actual-host acceptance is claimed. Complete native stages
through run_completed and reread the original architecture before the next major scope.

## Python material actually read

The exact current Work resolved docs.python:root and docs.python-practices:root.
The primary read local expressions.md Boolean operations and builtins.md all/any
implementations, plus the previously established object/mutability, ordinary bound
methods and explicit/simple-ownership guidance. Preserve evaluation and conversion
order, platform standard-library fnmatch semantics and native errors. No third-party
library or installation is needed.
