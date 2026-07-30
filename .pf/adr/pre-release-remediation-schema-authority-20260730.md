# ADR: authoritative contracts for pre-release remediation

- ADR id: `pre-release-remediation-schema-authority-20260730`
- Date: 2026-07-30
- Status: accepted for implementation
- Run: `pre-release-remediation-20260730`
- Assignment: `remediation-contract-architect-20260730`
- Related findings: `PF-AUD-001`—`PF-AUD-019`, `PF-AUD-023`—`PF-AUD-025`

## Context

The pre-release audit found that resource creators, JSON Schemas, doctors,
registries and release gates currently enforce different contracts. In
particular:

- public knowledge package ids are dotted, while the package schema rejects
  dots;
- the knowledge package creator exposes kinds not accepted by its schema;
- `template-create` produces a third implicit manifest shape between the two
  published template schemas;
- platform creators use different layouts and write registry entries without
  schema-required `name`;
- doctors can report `PASS` for invalid YAML or schema-invalid entities;
- authoring can publish partial state before postconditions are known;
- release consumer mode does not verify ZIP entry bytes;
- a stale linked-distribution override prevents launcher recovery.

This ADR freezes the contracts required to implement the remediation. It does
not authorize silent rewriting of existing workplace data.

## Decision 1: canonical resource id and path boundary

All path-addressed public resource ids for knowledge packages, reusable
templates and platforms use this lexical grammar:

```regex
^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$
```

Dots and dashes are both first-class namespace separators. Existing ids such
as `docs.php`, `docs.web.accessibility`, `platform.joomla` and dashed ids
remain valid.

Lexical validation is necessary but not a filesystem security boundary. Every
read and write resolver must also:

1. reject `/`, `\`, drive-qualified, rooted and UNC input;
2. reject colon, whitespace/control characters, `.` and `..` segments, percent
   encoded separators or traversal, and Windows trailing dot/space forms;
3. reject a Windows reserved device basename (`con`, `prn`, `aux`, `nul`,
   `com1`—`com9`, `lpt1`—`lpt9`) when the id becomes one path component;
4. resolve the declared root and target;
5. prove that the target is contained by the declared root;
6. fail before proposal, event, registry or filesystem mutation.

`safe_id` or any other lossy normalization is not accepted as validation.
Invalid user input must be rejected, not silently changed. The same primitive
must be used by create, import, add, doctor, hub build/release and lookup paths.

## Decision 2: knowledge package contract

`schemas/package-manifest.schema.json` is the authoritative contract for every
knowledge package manifest, including:

- installed package directories;
- `packs/official/*/knowledge-packages/*.yaml`;
- `seeds/knowledge-packages/*.yaml`;
- root public fixtures validated by the release schema gate.

The package `id` uses the canonical dotted/dashed grammar from Decision 1.

The authoritative `kind` vocabulary is the union of the existing schema
vocabulary and the public creator vocabulary:

```text
core
organization
direction
specialization
platform
toolchain
documentation
rules
source
mixed
project
process
task
agent_profile
```

`knowledge_package` is a structural object type, not a semantic package kind.
Hub generation must choose `documentation`, `rules`, `source` or `mixed`
according to its contents; it must not add `knowledge_package` to the enum.

Existing official and seed ids are preserved. Their validation coverage is
added to `validate-process-forge-schemas.py`; migration must not rename them.
Invalid YAML is never replaced by an in-memory synthetic manifest.

## Decision 3: template contracts

The two existing schemas describe two different resources and must not be used
interchangeably:

- a workplace reusable-template directory whose manifest is `template.yaml`
  uses `schemas/reusable-template.schema.json`;
- a portable payload manifest named `template-package.yaml` uses
  `schemas/template-package.schema.json`.

`template-create` creates the first resource only.

For the first public workplace reusable-template manifest,
`schema_version: 1` is authoritative. Required identity fields are:

```yaml
schema_version: 1
id: report.audit.basic
type: reusable_template
kind: document
title: Audit Report
version: 1.0.0
files: []
```

`kind` is one of `document`, `scaffold`, `prompt`, `assignment`,
`media_prompt`. `source_package` is optional for workplace-local authoring and
required when the reusable template is published through a package/catalog
profile. `inputs`, `outputs`, `prompts`, compatibility and modification-policy
fields remain valid schema properties.

`template-package.schema.json` retains the portable payload vocabulary
`file|media|prompt|directory|multi-file`; it does not validate a workplace
`template.yaml`.

Both contracts use the canonical dotted/dashed id grammar. Reusable-template
manifests use only the first public `schema_version: 1` contract. Superseded
pre-release shapes are invalid; shipped and dogfooding fixtures must be
migrated before validation. Doctors never rewrite legacy data.

## Decision 4: platform identity, registry and layout

A platform has two related identities:

- logical platform id in `registries/platforms.yaml`: the unprefixed canonical
  id, for example `joomla`;
- contract/package id in the contract and registry `package_id`:
  `platform.<logical-id>`, for example `platform.joomla`.

CLI input may use either form and is normalized without changing the stored
identity. The contract schema must enforce the `platform.` contract prefix and
the canonical id grammar.

Every platform registry entry requires:

```yaml
id: joomla
name: Joomla
package_id: platform.joomla
path: platform-contracts/platform.joomla/platform-contract.yaml
status: available
```

The canonical layout is the layout produced by `platform-create`:

```text
<platform-root>/platform.<id>/platform-contract.yaml
```

`platform-contract-install` must delegate to the same internal importer and
transaction or be deprecated in favour of it. It must not create
`platforms/<id>/platform.yaml`. The legacy layout remains readable for one
compatibility window and produces a migration `WARN`; a same-id import must
never silently redirect the registry and orphan the canonical contract.

`available` is published only after schema, semantic and readiness checks pass.
Failed authoring leaves no active registry entry.

## Decision 5: doctor contract

Every doctor executes the same ordered layers:

1. resolution and existence;
2. YAML parse;
3. validation against the authoritative JSON Schema selected by resource type
   and schema version;
4. identity match, path containment and public-safety checks;
5. semantic references and lifecycle invariants;
6. readiness and optional health checks.

The result policy is:

- parse, schema, containment, required reference or invariant violation:
  `FAIL`, exit `1`;
- optional missing resource, supported legacy migration or deprecation:
  `WARN`, exit `0` in a standalone non-strict doctor;
- clean result: `PASS`, exit `0`;
- `--strict` and release policy may promote `WARN` to nonzero.

Doctors are observational. They must not repair or reset an entity or registry,
publish availability, write a platform snapshot, or append a state-changing
event. An explicitly requested diagnostic report may be written to its
declared artifact sink, but report generation must not change the governed
health result.

A corrupt registry remains byte-for-byte unchanged. Register/upsert operations
must fail preflight rather than replace invalid YAML or a wrong collection
type with an empty registry.

## Decision 6: authoring transaction

Every authoring apply uses one transaction contract:

1. validate ids and secret references before proposal or events;
2. compute the complete write set;
3. preflight roots, parent types, collisions, registry parse/schema and
   immutability rules;
4. stage content on the same filesystem as its destination;
5. validate schemas and doctor postconditions against the staged/virtual view;
6. atomically publish the entity files or directory;
7. atomically update the registry last;
8. on any error, restore backups or remove newly published state using the
   transaction journal;
9. verify the committed state before publishing terminal events.

For multi-file updates that cannot be made physically atomic as one rename,
the required product guarantee is failure atomicity through a write-ahead
journal, same-filesystem staging, atomic per-file replace and rollback.

`available`, `registered` and `authoring.completed` are emitted only after a
durable commit and successful postcondition doctor. A failure may emit a
terminal failed audit event after rollback; it must not emit `completed`.
Dry-run lists the same complete write set as apply.

`--force` does not bypass path containment, schema validation, transaction
preflight or immutable same-version process rules.

## Decision 7: public gate and archive integrity

`public-gate` is a real release-test group. It expands to every command whose
release metadata has `public_gate: true` and to `public_release_checks`.

- `--only public-gate` runs the expanded group;
- `--skip public-gate` excludes that group and the public checks;
- an accidentally empty selection is a configuration `FAIL`;
- aggregate exit status is failure if any selected process or resource check
  fails;
- no aggregator may return only one sub-result while its report says `FAIL`.

Release manifest version 1 is the first public consumer-verifiable sidecar
containing:

- SHA-256 and size for every ZIP entry;
- total entry count;
- SHA-256 of the final ZIP;
- package name/version and schema bundle version;
- Git commit and tree ids;
- `dirty: false`;
- official pack inventory;
- deterministic build timestamp/source-date metadata.

Consumer mode verifies the ZIP hash and actual bytes of every entry, as well
as missing, extra, duplicate, case-fold-colliding and unsafe names, without a
source checkout. This proves consistency of the distributed ZIP/manifest pair;
publisher authenticity requires an external signature and is outside this
remediation slice.

The embedded checksum inventory covers every shipped file except the checksum
file itself. Public release packing requires a clean Git state. A dirty
development archive is allowed only through an explicit non-public override,
must record `dirty: true`, and is not eligible for release delivery.

## Decision 8: linked launcher precedence

The project-local launcher evaluates candidates in this order:

1. a valid explicit project-local `distribution_override`;
2. a valid workplace distribution registry entry;
3. a valid `PROCESSFORGE_HOME`.

A candidate is valid only when the resolved root exists and contains the
expected ProcessForge CLI. A missing or stale higher-precedence candidate is a
diagnostic and the resolver continues to the next candidate; it is not a
terminal selection.

When no candidate is valid, the failure lists every source tried, the resolved
path and rejection reason. When a fallback wins over a stale candidate, the
launcher emits a concise warning and the repair command. No automatic rewrite
of the project or workplace link occurs.

## Compatibility and migration

The compatibility policy is expand, migrate, then tighten:

1. first expand readers and schemas to recognize existing valid dotted ids and
   explicitly model supported legacy template/platform layouts;
2. migrate all shipped official, seed, template and registry fixtures;
3. add dry-run/apply migration tooling for existing workplaces;
4. make all new writes use the authoritative forms;
5. keep legacy reads for a documented transition with `WARN`;
6. remove legacy write paths before the public release; remove legacy reads
   only in a separately versioned breaking release.

Migration is explicit, reportable and rollback-capable. It preserves ids and
versions, records source/target paths and hashes, and never runs as a side
effect of doctor.

## Implementation constraints

- Security validation and containment must be centralized and reused; regexes
  copied among commands are not sufficient.
- Schema validation must use the same helper in creators, doctors and release
  validation.
- Schema/generator/doctor changes for one entity ship in the same slice.
- Registry mutation must use parse/schema-preserving atomic update.
- Existing user data is not silently defaulted, renamed or overwritten.
- Negative regression tests must prove both nonzero exit and absence of
  filesystem, registry and success-event mutation.
- Source, extracted archive and consumer-only archive tests must exercise the
  same contract.

## Rejected alternatives

- **Ban dotted ids.** Rejected because official and seed package identities
  already use dots and dots express the established namespace model.
- **Treat both template schemas as equivalent.** Rejected because their
  required fields and payload semantics describe different resources.
- **Add `knowledge_package` to package kind.** Rejected because it confuses
  structural resource type with content semantics.
- **Let doctors repair invalid registries.** Rejected because a diagnostic
  command must not hide corruption or cause data loss.
- **Stop on the first stale launcher override.** Rejected because it defeats
  linked-distribution relocation and the documented fallback mechanisms.
- **Verify entry names only in consumer mode.** Rejected because it cannot
  detect changed archive contents.

## Consequences

The release schemas become broader where compatibility requires it (dotted
ids and existing package kinds) and stricter where identity or lifecycle
guarantees require it. Some existing locally generated template/platform
artifacts will show migration warnings until explicitly upgraded. This is
preferable to silent rewriting or false-green doctors.

Implementation agents may proceed against this ADR. Any change to the id
grammar, template profile split, platform stored identity, doctor exit policy,
transaction event order, release manifest integrity fields or launcher
precedence requires a follow-up ADR before implementation.
