# Platform Hardcode Cleanup Report

- timestamp: 2026-07-19 17:27 +04:00
- source assignment: `задания/processforge_platform_hardcode_cleanup_prompt.md`
- status: release_validated

## Removed From Core

Removed platform/package-specific core logic from `tools/processforge.py`:

- Python platform contract constant for Example Parent Platform.
- Required-parent constant for Example Child Platform and Example Child Platform.
- Example Parent Platform project type and directory/file detection branches.
- Package doctor branches for Example Child Platform and Example Child Platform dependencies.
- Base-technology platform id constant.
- API generic package id branch.
- Example Parent Platform-specific workplace doctor check.

`tools/processforge.py` now has no matches for the required hardcode grep
patterns.

## Data Locations

Seed platform manifests live in:

- `seeds/platform-contracts/platform.example-parent.yaml`
- `seeds/platform-contracts/platform.example-child.yaml`
- `seeds/platform-contracts/platform.example-child.yaml`

Seed knowledge package manifests live in `seeds/knowledge-packages/`, including
the accepted demo stack packages and base technology knowledge packages.

Policy manifests live in:

- `policies/platform-id-policy.yaml`
- `policies/package-id-policy.yaml`
- `policies/core-hardcode-policy.yaml`
- `policies/public-support-policy.yaml`

## Generic Resolver

Platform resolution now loads manifests from seed, project, and workplace
locations. It selects platforms from explicit inputs, `project_type_hints`, and
generic `detection` rules. The resolver reads `extends`,
`requires.platforms`, `requires.*`, `includes.*`, capabilities, tools, MCP,
templates, and processes without checking concrete platform ids.

The graph resolver remains parent-first, detects missing parents, detects
circular inheritance, merges resources by id, and writes deterministic
`platform_stack` and `knowledge_stack` records.

## Package Dependencies

Knowledge package dependencies are manifest-driven. Doctors read
`dependencies` and `requires.knowledge_packages` for any package id. Platform
resolution expands required package dependencies generically so a package can
bring its own required parent package without a Python branch.

## Detection

Platform detection interprets manifest fields generically:

- `detection.project_type_hints`
- `detection.directories.any`
- `detection.directories.all`
- `detection.files.any`
- `detection.files.all`
- `detection.file_contains`

Synthetic smoke manifests demonstrate file detection through the neutral
`processforge-test.project` marker. Real project domains can define equivalent
detection rules in their own platform manifests.

## Grep Summary

Required grep command was run against the repository.

Classified results:

- `tools/processforge.py`: zero matches.
- `tools/validate-process-forge-schemas.py`: zero matches.
- Allowed policy data: `policies/core-hardcode-policy.yaml`.
- Allowed seed manifests: accepted demo stack and base technology knowledge
  packages under `seeds/`.
- Allowed examples/templates/docs/smoke artifacts: Example Parent Platform/Example Child Platform/Example Child Platform
  remain as domain examples only.
- Historical `.pf/artifacts/` and `.pf/reviews/` entries were updated where they
  previously described the model as built-in.

## Smoke Results

- `python tools/smoke_manifest_driven_platforms.py`: PASS.
- `python tools/smoke_platform_inheritance.py`: PASS.

`tools/smoke_manifest_driven_platforms.py` proves inheritance with
`platform.test-parent -> platform.test-child` and detects
`platform.test-file-detection` from `processforge-test.project` via manifest
rules.

## Release Results

- `python -m py_compile tools/processforge.py tools/smoke_platform_inheritance.py tools/smoke_manifest_driven_platforms.py tools/validate-process-forge-schemas.py`: PASS.
- `python tools/smoke_manifest_driven_platforms.py`: PASS.
- `python tools/smoke_platform_inheritance.py`: PASS.
- `python tools/validate-process-forge-schemas.py --root .`: PASS.
- `python tools/validate-public-cleanliness.py --root .`: PASS.
- `python tools/validate-process-forge-checksums.py --root . --check`: PASS.
- `python bin/pf.py release-test --root .`: PASS.
- `python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip`: PASS.
- `python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip`: PASS.
- `git diff --check`: PASS.

## Remaining Boundary

Concrete platform ids are allowed only when they are intentional demo stack data
or policy data. Core ProcessForge logic must stay domain-agnostic.
