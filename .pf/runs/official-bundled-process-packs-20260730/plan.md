# Run Plan: Official Bundled Process Packs

Objective: Introduce first-class official bundled process packs while preserving a domain-neutral ProcessForge kernel.

## Architecture

1. Keep `processes/core/**` and generic runtime algorithms domain-neutral.
2. Add `packs/official/*/package.yaml` as a distinct production distribution layer.
3. Discover official pack manifests generically; keep domain identifiers in pack data only.
4. Record explicit workplace activation in `registries/process-packs.yaml`.
5. Resolve workplace profiles from each manifest's `activation.profiles` data.
6. Expose available and active pack processes through the generic process catalog.
7. Load classifiers and declared capabilities only from active packs.
8. Preserve workspace/project/custom process precedence over official and core entries.
9. Keep inactive official processes discoverable through `--available` and `process-show`, but reject them for execution with an activation hint.
10. Move the five stable production processes from `examples/domain-packs/**` to `packs/official/**`; leave examples as consumers only.

## Workstreams

- `root`: generic CLI/runtime catalog, activation, profile, classifier/capability integration, release command registration.
- `pack-data-analyst`: official pack data migration and example usage references.
- `qa-docs-analyst`: schemas, validators, public inventories, policies, EN/RU docs, and deterministic smoke files.
- Review starts only after all implementation workstreams are integrated.

## Acceptance Gates

- Ten official-pack smokes.
- Previous domain-neutral and capability/specialization/project-override smokes.
- Schema, public-cleanliness, checksum, catalog doctor, public release-test.
- Canonical release archive plus full extracted archive test.
- Dogfooding report, review, handoff, task/run doctors, and `git diff --check`.
