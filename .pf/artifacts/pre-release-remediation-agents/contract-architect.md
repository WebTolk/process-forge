# Contract architect report

- Run: `pre-release-remediation-20260730`
- Assignment: `remediation-contract-architect-20260730`
- Agent Ledger identity: `codex-remediation-contract`
- Session: `pre-release-remediation-20260730-contract`
- Lease: `lease-remediation-contract-20260730`
- Result: `completed`
- Product code changes: none

## Outcome

The remediation contracts are frozen in
`.pf/adr/pre-release-remediation-schema-authority-20260730.md`. The decisions
preserve existing official dotted identities while removing the ambiguity
between creators, schemas, doctors and release gates.

## Decisions

1. Path-addressed resource ids use lowercase dotted/dashed segments. Raw path
   forms, traversal and Windows device/path edge cases are rejected before any
   proposal or mutation, followed by resolved-root containment.
2. `package-manifest.schema.json` is authoritative for installed, official and
   seed knowledge manifests. Existing and creator package kinds are unified;
   `knowledge_package` is not a semantic kind.
3. Workplace `template.yaml` and portable `template-package.yaml` remain
   distinct contracts. New workplace manifests use reusable-template version
   2; legacy version 1 remains readable with a migration warning.
4. Platform contracts use `platform.<logical-id>`, while the registry stores
   the unprefixed logical id and a required `name`. Both platform masters must
   share the canonical platform-contract layout and transaction.
5. Doctors use parse, schema, containment, semantics and readiness layers.
   They are observational and must not synthesize, repair or reset data.
6. Authoring uses preflight, same-filesystem staging, staged validation,
   atomic publication, registry-last commit and journalled rollback.
7. `public-gate` becomes a real command group. Consumer archive validation
   hashes the ZIP and every entry without needing source.
8. Launcher precedence is valid local override, valid workplace registry,
   valid environment fallback. Stale candidates warn and fall through.

## Compatibility and migration

- Official dotted package ids are retained unchanged.
- Package schema expansion is backward-compatible.
- Existing reusable-template version 1 and legacy platform layouts remain
  readable for a documented transition, but all new writes use authoritative
  forms.
- Migration is explicit, dry-run capable, rollback-capable and never a doctor
  side effect.
- Shipped official/seeds/templates/registry fixtures must be migrated before
  the public release gate can pass.

## Evidence reviewed

- `.pf/artifacts/pre-release-product-audit-20260730.md`
- `.pf/artifacts/pre-release-remediation-plan-20260730.md`
- `schemas/package-manifest.schema.json`
- `schemas/reusable-template.schema.json`
- `schemas/template-package.schema.json`
- `schemas/platform-registry.schema.json`
- `schemas/platform-contract.schema.json`
- `templates/reusable-template-template.yaml`
- `templates/template-package.yaml`
- `templates/knowledge-package.yaml`
- `templates/platform-contract.yaml`
- `packs/official/*/knowledge-packages/*.yaml`
- `seeds/knowledge-packages/*.yaml`
- relevant creator, doctor, release gate and launcher paths in
  `tools/processforge.py`

The evidence confirms that the chosen dotted/dashed grammar matches existing
official package identities and the current public creator UX, while the
published package schema currently rejects those same identities.

## Implementation constraints

- The schema alignment agent should treat the ADR as authoritative and update
  schemas, generators, fixtures and schema-test coverage as one coherent
  change.
- The core implementation writer should introduce one shared resource-id and
  containment primitive instead of per-command checks.
- Doctor wiring must never call a loader that turns invalid YAML into defaults.
- Upsert must fail on corrupt registries and preserve original bytes.
- Platform availability and completed events are post-commit outcomes only.
- Release consumer tests must mutate entry bytes while retaining names to
  prove that hash verification is active.
- Launcher relocation tests must cover stale local and workplace candidates
  followed by a valid environment candidate.

## Risks

1. Supporting legacy and version 2 reusable templates in one schema can become
   an ambiguous union. Select branches by `schema_version` and `type`, and add
   fixtures proving that invalid hybrid shapes fail.
2. Physical atomicity across an entity root and a separate registry is not
   portable. The implementation must test the journalled rollback guarantee,
   not claim an unsupported multi-file atomic rename.
3. Widening a shared id definition beyond the three named resources could
   unintentionally admit dots to lifecycle ids. Scope the shared grammar by
   resource family unless a separate inventory proves broader compatibility.
4. A ZIP hash in an unsigned sidecar proves pair integrity, not publisher
   authenticity. Do not describe it as a signature.
5. A valid but unintended old local override remains higher precedence than
   the environment by design. Diagnostics should display the selected source;
   an explicit CLI override can be added later if operator override is needed.

## Recommended implementation order

1. Add shared id/containment and secret-reference preflight.
2. Align package/template/platform schemas, generators and shipped fixtures.
3. Wire authoritative schema validation into observational doctors and safe
   registry mutation.
4. Introduce the shared authoring transaction and platform layout migration.
5. Fix aggregate public gates, consumer integrity and provenance.
6. Fix launcher fallback and run source, dogfooding and extracted archive
   regressions.

## Files changed

- `.pf/adr/pre-release-remediation-schema-authority-20260730.md`
- `.pf/artifacts/pre-release-remediation-agents/contract-architect.md`

No product code, schema, template, pack, seed, documentation, checksum or
release archive file was changed.
