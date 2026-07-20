# Changelog

## 1.0.0 - 2026-07-20

### Added

- Promoted ProcessForge distribution, schema bundle, generated project flow
  manifests, process definitions, packages, templates, examples, and update
  index to `1.0.0`.
- Added a stable update-index entry for checking upgrades from `0.1.0` to
  `1.0.0`.

### Changed

- Human documentation now starts from workplace/device abstractions and separates
  ProcessForge core mechanics from workplace/project resources.
- Agent documentation and prompts now prefer implemented `bin/pf.py` commands.
- Platform contracts remain data-driven composition manifests; ProcessForge core
  stays platform-agnostic.

## 0.1.0-rc.1 - 2026-07-18

### Added

- Added release validation through `release-test` and `smoke-all`.
- Added release hygiene cleanup, examples verification, release packaging, manifest generation, and version reporting.
- Added docs index, v0.1 release notes, and known limitations.

### Changed

- Hardened resource-authoring smoke tests with subprocess timeouts, isolated scenarios, and clearer diagnostics.
- Strengthened release checks for generated cache files, private/local data, unsupported script wrappers, and stale public examples.
- Updated public quickstart and examples to prefer Python launchers.

### Known Limitations

- File-only, single-agent flow is the supported v0.1 release candidate scope.
- Hooks remain observational and outbox-only.
- Multi-agent coordination, runner/supervisor, daemon, GUI, marketplace, remote sync, and publish services remain future work.

## 0.1.0 - 2026-07-13

- Created the clean-start file-only ProcessForge bootstrap.
- Added root manifest, agent rules, concepts, authoring guides, schemas, seed processes, packages, templates, examples, validators, assignments, artifacts, reviews, handoffs, and ADRs.
- Established public-cleanliness, file-only operation, immutable execution context, and safe process evolution policies.
