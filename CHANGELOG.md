# Changelog

## Unreleased

## 1.0.2 - 2026-08-05

### Changed

- Simplified the update server contract to rely on `manifest_url` and
  `changelog_url` instead of provider-specific update site types.
- Updated the update documentation to describe server-based manifests and local
  file manifests without legacy `url` compatibility wording.
- Updated runtime-driver documentation to match the current shell-agent launch
  flow and model/reasoning selection behavior.

### Fixed

- Aligned update-site validation, schema fixtures, and update discovery smokes
  with the providerless update server model.

## 1.0.1 - 2026-08-04

### Added

- Added first-class worker `workspace_access` grants for workplace knowledge,
  templates, tools, and MCP references without copying shared resources into
  project artifacts.
- Added private worker runtime access maps under
  `.pf/runtime/agent-runs/<run>/<task>/workspace-access.json`.
- Added the built-in `codex-exec` runtime driver and portable Codex CLI worker
  wrapper.
- Added smoke coverage for workspace access resolution, public path hygiene, and
  the `codex-exec` launch path.
- Added optional shell-agent model selection for multi-agent shell runs through
  `orchestrator-shell-plan-apply --model <model>`, propagated to generated
  worker metadata, environment, and runtime-driver command arguments.
- Added locked official pack activation to protect `process-packs.yaml` from
  concurrent `pack-activate` writers.
- Added inactive classifier suggestions when a project matches a classifier from
  an official pack that is available but not active.
- Added explicit runtime-access capability waivers for `doctor-project` registry
  declaration gaps.

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
