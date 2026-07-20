# Neutral Public Surface Cleanup Report

- timestamp: 2026-07-19 18:05 +04:00
- source assignment: `processforge_neutral_public_surface_cleanup_prompt.md`
- status: release_validated

## Scope

This slice keeps the public v0.1 surface neutral. Real ecosystems discussed
during design must not become advertised support packs unless the product ships
an intentional manifest package for them. Flow artifacts and core files must
describe process mechanics, not a specific platform stack.

## Changes

- Removed domain-specific built-in seed support packs from the core surface.
- Replaced domain-specific detection smokes with synthetic manifests:
  `platform.test-parent`, `platform.test-child`,
  `platform.test-file-detection`, `docs.test-parent`, `docs.test-child`, and
  `docs.test-file-detection`.
- Replaced domain-specific project fixtures with neutral marker files.
- Process authoring example generation now derives report, review, and handoff
  filenames from any `process_id`.
- Public process authoring examples now use neutral process ids.
- Provider examples use neutral placeholder ids such as
  `docs.api.example-provider`, `platform.api-example-provider`, and
  `api-example-provider`.
- Added `policies/public-support-policy.yaml` and wired release checks to read
  blocked public support patterns from YAML.
- Neutralized public templates, seeds, tests, and flow artifacts that described
  real platforms as built-in support data.
- Platform inheritance is demonstrated by neutral parent/child fixtures in
  flow and core artifacts. Real platform inheritance examples belong only in
  documentation.

## Grep Classification

Required grep command:

```bash
rg -n "<real-platform-or-provider-marker>" . --glob '!docs/**' --glob '!examples/**'
```

Classification after implementation and checksum regeneration:

- Removed from seeds, templates, tools, process mechanics, and flow artifacts.
- Kept only as documentation/example prose where a real stack is intentionally
  used to illustrate platform inheritance.
- Removed stale `dist/processforge-release.*` artifacts that contained old
  manifest paths.
- Neutral parent/child manifests remain intentional demo data, not core logic.

## Required Validation

Final validation results:

- `python tools/smoke_manifest_driven_platforms.py`: PASS.
- `python tools/smoke_platform_inheritance.py`: PASS.
- `python tools/validate-process-forge-schemas.py --root .`: PASS.
- `python tools/validate-public-cleanliness.py --root .`: PASS.
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS after inventory regeneration.
- `python bin/pf.py release-test --root .`: PASS.
- `python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip`: PASS.
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip`: PASS.
- `git diff --check`: PASS.

## Boundary

Users can still define any platform in their own manifests. ProcessForge core,
flow artifacts, built-in seeds, templates, and smoke fixtures must remain
platform-agnostic. Concrete platform examples are documentation-only.
