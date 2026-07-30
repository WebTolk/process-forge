# ADR: provider, classifier and runtime-driver contracts

- ADR id: `pre-release-remediation-provider-runtime-design-20260730`
- Date: 2026-07-30
- Status: accepted for implementation
- Run: `pre-release-remediation-20260730`
- Assignment: `remediation-provider-runtime-design-20260730`
- Related findings: `PF-AUD-012`, `PF-AUD-013`, `PF-AUD-021`, `PF-AUD-022`
- Extends: `pre-release-remediation-schema-authority-20260730`

## Context

The current provider commands, process definitions, schemas and doctors describe
different products:

- `command_tool_register` and `command_mcp_register` mutate registries after a
  proposal but do not produce or enforce the request, definition, validation and
  review artifacts declared by the public processes;
- `command_mcp_register` checks `args.command` for obvious secrets but stores
  `args.auth_ref` without validating whether it is a reference or a literal;
- the secret heuristic does not recognize common bare-token shapes such as
  `sk-*`;
- `minLength: 1` and unconstrained registry strings accept whitespace-only
  capability, command, transport and healthcheck values;
- classifier support is consumer-only and silently skips malformed registries
  or documents;
- runtime drivers have list, single validate and describe commands, but no
  governed authoring, registry doctor or validate-all surface;
- runtime list and resolution implement opposite same-id precedence;
- worker execution performs semantic runtime-driver checks without first
  enforcing `runtime-driver.schema.json`.

The common authoring transaction and doctor ordering from the parent ADR remain
mandatory.

## Decision 1: public provider commands are governed masters

`tool-register` and `mcp-register` remain the public implementation of the
processes with the same ids. They are not renamed into low-level registry
mutators. `upsert_registry_entry` remains an internal commit primitive and must
never be exposed as an equivalent public success path.

Both commands use two explicit phases:

1. `--dry-run` is observational and prints the complete prepare/apply write set.
2. `--prepare` validates all input and the existing registry, then writes:
   - registration request/proposal;
   - schema-valid provider definition;
   - validation report with a SHA-256 of the definition.
   It does not update the registry and emits no `*.registered` event.
3. `--apply --proposal <path> --review <path>` consumes the prepared proposal.
   Raw provider fields are not accepted during apply. Apply verifies:
   - proposal and definition identity;
   - unchanged definition SHA-256;
   - a review conforming to `review.schema.json`;
   - `reviewed_object` bound to the provider kind, id and definition SHA-256;
   - `result: pass`;
   - an empty `blocking_issues` collection;
   - registry parse/schema and collision preconditions;
   - provider schema, semantics and readiness;
   - configured-provider healthcheck.
4. The registry is committed last. Only after committed-state verification may
   the command emit `tool.registered`/`mcp.registered` and the matching
   healthcheck event.

`pass_with_conditions`, `warn`, `skipped` and `fail` do not satisfy the blocking
review gate. `--apply` without an independently supplied passing review fails
without registry, proposal, report or success-event mutation.

The existing `--dry-run` behavior that writes a proposal is removed. A
compatibility message directs callers that need a durable proposal to
`--prepare`.

## Decision 2: secret references are structural, not heuristic

The canonical MCP definition and registry entry contain an `auth` field with
exactly one of these shapes:

```yaml
auth: null
```

```yaml
auth:
  secret_ref: provider.github.token
```

```yaml
auth:
  env_ref: GITHUB_TOKEN
```

The contracts are:

- `secret_ref` uses the canonical resource-id grammar
  `^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$`;
- `env_ref` is an environment variable name matching
  `^[A-Z_][A-Z0-9_]*$`;
- `secret_ref` and `env_ref` are mutually exclusive;
- `auth: null` is the only no-auth representation written by new code;
- values resolved from a secret store or environment are never serialized into
  proposals, definitions, registries, reviews, reports or events.

The CLI exposes a mutually exclusive group:

- `--secret-ref <id>`;
- `--env-ref <ENV_NAME>`;
- `--no-auth`.

The old `--auth-ref` option and `auth_ref` field are removed. Any occurrence is
a schema/CLI error; there is no compatibility reader or migration warning.

Field-driven schema and semantic validation is the security boundary.
`contains_secret_value` is strengthened and retained only as defense in depth.
It must scan command, healthcheck, proposal, definition and registry values and
recognize at least assignment-style credentials, PEM private keys, bearer
tokens, common `sk-*`/`gh*_*` token families and JWT-like values. Heuristic
acceptance can never turn an invalid auth shape into a valid reference.

## Decision 3: provider definition and readiness contract

Tool and MCP ids use `validate_resource_id`; lossy `safe_id` is forbidden.
Names, capabilities, commands, transports and healthcheck commands are
normalized with `strip()` and then required to contain a non-whitespace
character. Capability values remain opaque and may contain established
underscores or dots.

The definition and registry schemas must enforce the same field rules:

### Tool

Required operational fields:

```text
id, name, capability, command, scope, status, healthcheck
```

`scope` is `workplace` for this surface. `healthcheck.command` is explicit;
`<command> --version` is not synthesized.

### MCP

Required operational fields:

```text
id, name, capability, transport, command, auth, status, healthcheck
```

Transport is an opaque nonblank identifier until a protocol-specific schema is
introduced. A configured stdio provider still needs a separate bounded
healthcheck command; launching a potentially long-lived server is not treated
as a generic healthcheck.

### Status and health

- `configured`: schema and semantic checks pass, a bounded healthcheck is
  declared, and apply healthcheck exits successfully;
- `optional`: definition is valid, but absence/readiness failure is a warning
  and the provider does not satisfy a required capability;
- `missing`: definition records an unavailable provider and is never healthy;
- `disabled`: definition is intentionally inactive and is never healthy.

Only a valid configured provider is included in required capability
resolution. `registry_ids` must not be used to turn every id/capability,
including missing or disabled entries, into availability.

Add observational `tool-doctor` and `mcp-doctor` commands. `doctor-workplace`
calls their schema and semantic layers. External healthchecks run only during
configured-provider apply or when explicitly requested with
`--run-healthchecks`; readiness checks that do not start a provider always run.

## Decision 4: classifier authoring and resolution

Add a governed `project-classifier` command group:

```text
project-classifier create
project-classifier register
project-classifier doctor
```

`create` accepts a canonical id, nonblank name and a rules document and writes
`<scope-root>/project-classifiers/<id>.yaml`. `register` imports a complete
schema-valid manifest into that canonical location; registries never point to
arbitrary external paths. Both use dry-run/prepare/review/apply and the common
transaction, publishing the registry entry last.

The registry path is canonical and relative:

```yaml
id: example.classifier
path: project-classifiers/example.classifier.yaml
status: active
```

The doctor checks, in order:

1. registry existence, YAML parse and
   `project-classifier-registry.schema.json`;
2. duplicate ids within one source;
3. path containment and canonical path;
4. manifest YAML and `project-classifier.schema.json`;
5. registry/manifest/file-name id equality;
6. non-empty rule collection and rule semantics;
7. active/disabled resolution.

Classifier precedence is:

```text
project > workplace > active package
```

A higher-precedence disabled entry is a tombstone and prevents fallback to a
lower active same-id classifier. Same-id duplicates in one source are a
blocking error. Different classifier ids are cumulative and may all
participate in classification.

`project_classifier_registry_documents`, `project_classifier_paths` and
`classify_project` consume one shared provenance-aware resolution. They never
silently omit a malformed required registry or registered manifest.

Add the public process `project-classifier-authoring` and register it in public
process/schema inventories.

## Decision 5: runtime-driver authoring, doctor and provenance

Extend the existing `runtime-driver` group:

```text
runtime-driver create
runtime-driver register
runtime-driver doctor
runtime-driver validate-all
```

`create` materializes a canonical manual or shell manifest. `register` imports a
complete manifest into the selected workplace or project-local canonical
runtime-driver directory. Both use the common dry-run/prepare/review/apply
transaction and publish the registry last.

Every read path uses one resolution record containing at least:

```text
id
declared_status
computed_health
source_scope
registry_path
manifest_path
selected
candidates
checks
```

Precedence is:

```text
project > workplace > distribution > builtin fallback
```

A selected higher-scope `disabled` or `missing` entry blocks fallback. A
same-id duplicate in one registry is `FAIL`. Registry order does not decide
precedence. `list`, `describe`, single validate, validate-all, doctor and worker
execution all consume the same selected record, so displayed provenance is the
executed provenance.

Runtime-driver validation layers are:

1. registry parse/schema;
2. registry identity, duplicate and path-containment checks;
3. manifest YAML and `runtime-driver.schema.json`;
4. registry/manifest id equality;
5. placeholder allow-list and reserved environment keys;
6. kind-specific semantics;
7. readiness.

For `kind: shell`, schema/semantics require a nonblank executable, an args
array, bounded limits, `allow_shell: false`, and `allow_network: false`.
For `kind: manual`, `behavior.do_not_start_process: true` is required.
`PF_AGENT_EXIT_PATH` is added to the schema's reserved environment keys to
match runtime enforcement.

`runtime_driver_for_task` must run the complete schema/semantic resolution
checks. A direct unregistered manifest may be inspected by validate/describe,
but worker execution uses a registered id unless the operator explicitly opts
into an unregistered path and it passes the same complete checks.

## Decision 6: schema and process parity

The following schemas are one inseparable implementation slice:

- `tool-definition.schema.json`;
- `tool-registry.schema.json`;
- `mcp-definition.schema.json`;
- `mcp-registry.schema.json`;
- `project-classifier.schema.json`;
- `project-classifier-registry.schema.json`;
- `runtime-driver.schema.json`;
- `runtime-driver-registry.schema.json`.

Whitespace-sensitive strings use a non-whitespace pattern, not `minLength`
alone. Definition templates and all four registry templates are mapped to
their schemas in `validate-process-forge-schemas.py`.

In `tool-register.yaml` and `mcp-register.yaml`, provider definitions are YAML,
not the current contradictory Markdown artifact backed by a YAML template.
The process artifacts, gates, CLI modes and event order must exactly describe
the implemented two-phase master. `runtime-driver-registry.yaml` is expanded to
cover create/register/doctor/validate-all and its duplicated
`process-forge-core` package entry is removed.

## Transaction and failure invariants

Every negative precondition fails before a proposal or state mutation.
Prepared artifacts are immutable inputs to apply. Apply failure preserves:

- registry bytes;
- existing definition bytes;
- classifier/driver directories;
- previous health state;
- absence of registered/completed success events.

A failed healthcheck may emit only a redacted failure audit event after proving
that no registry/entity commit occurred. No event or report may contain command
output that has not passed secret redaction.

## Implementation ownership

Start only after the current owner of `tools/processforge.py` has released its
lease. One implementation owner has the sole write scope for:

- `tools/processforge.py`;
- `tools/validate-process-forge-schemas.py`;
- the eight schemas listed in Decision 6;
- `templates/tool-definition.yaml`;
- `templates/mcp-definition.yaml`;
- `templates/project-classifier.yaml`;
- `templates/registries/tools.yaml`;
- `templates/registries/mcp.yaml`;
- `templates/registries/project-classifiers.yaml`;
- `templates/registries/runtime-drivers.yaml`;
- affected `templates/runtime-drivers/*.yaml`;
- `processes/core/tool-register.yaml`;
- `processes/core/mcp-register.yaml`;
- `processes/core/runtime-driver-registry.yaml`;
- new `processes/core/project-classifier-authoring.yaml`;
- matching EN/RU concept, process and CLI documentation;
- dedicated provider/classifier/runtime remediation smokes;
- public release-command registration for those smokes.

No parallel writer may edit any file in this scope. A separate reviewer runs
only after the implementation owner freezes the slice.

## Required regression matrix

### Provider security and parity

- whitespace-only id/name/capability/command/transport/healthcheck;
- path-like and Windows-reserved provider ids;
- raw `sk-*`, bearer, PEM, assignment-style and JWT-like secrets in every
  serialized or executable field;
- valid `secret_ref`, valid `env_ref`, explicit no-auth;
- invalid/lowercase env ref, both refs, neither explicit auth mode;
- every legacy `auth_ref` input or field fails;
- apply without review, stale definition hash, non-pass review and blocking
  issue;
- configured provider healthcheck pass/fail/timeout;
- optional, missing and disabled provider capability resolution;
- corrupt registry followed by prepare/apply;
- success artifact/event completeness and order.

### Classifier

- create and register produce schema-valid canonical files;
- malformed/missing registry, wrong collection and duplicate id;
- external/traversing registry path and id mismatch;
- empty rules and malformed rule;
- active package/workplace/project same-id precedence;
- higher disabled tombstone;
- doctor is observational and preserves bytes.

### Runtime driver

- create/register for manual and shell;
- missing/blank executable and invalid args;
- reserved environment override including `PF_AGENT_EXIT_PATH`;
- unknown placeholder and invalid limits;
- malformed/missing registry and duplicate id;
- distribution/workplace/project same-id precedence;
- higher disabled/missing tombstone;
- list provenance equals describe, validate and worker execution provenance;
- validate-all includes every selected entry and reports invalid skipped
  candidates;
- doctor is observational and preserves bytes.

All negative tests assert nonzero exit and byte-for-byte absence of registry,
entity and success-event mutation. The dedicated smokes are included in source,
public release, extracted-archive and consumer archive validation.

## Consequences

Provider registration becomes intentionally two-step because a blocking review
cannot be truthfully self-approved by the mutating command. Internal fixtures
with `auth_ref` must be migrated before validation; every `auth_ref` value is a
release-blocking failure.

Classifier and runtime-driver resolution gain explicit provenance and
tombstones. This removes the current contradiction where list displays a
workplace/project override while execution selects the distribution entry.

The slice is larger than a local CLI patch, but schema, generator, doctor,
process and release validation cannot be safely shipped independently for these
entities.
