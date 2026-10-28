# Changelog

## Unreleased

## 1.3.0-beta1 - 2026-10-26

### Changed

- Prepare the beta1 source candidate from the existing alpha6 development
  checkpoint. This release-identity change adds no functionality.
- Document the existing owned worker scratch lifecycle and retention boundaries;
  required input, recovery data and durable evidence remain protected.
- Define the Core update policy: confirmed updates must converge all
  release-owned Core files to qualified target release bytes, replacing local
  edits even when official bytes are unchanged between releases. Preserve actual
  replaced or removed preimages, including missing-file absence, in the existing
  recovery backup. Existing flags remain accepted; force is not required solely
  for local Core edits and cannot bypass authority, ownership, selection, path,
  collision or safety checks. Unknown non-owned files, configuration, project and
  Workplace data, and runtime state retain their existing handling. The first
  update from 1.2.0 retains its handoff, confirmation and recovery requirements.
  Final implementation matching and normal documentation/release checks remain
  mandatory.

### Fixed

- Preserve committed scratch bindings on prepare retry and recover unpublished
  worker scratch before retry; retain explicit cancellation and cleanup results.
- Preserve sealed release reports, child failure output and extracted release
  evidence before disposal.
- Restore `release-archive-test` without `--root`, retaining explicit-root source
  verification and the existing default evidence root.

### Qualification

- This is a source candidate, not a publication or beta acceptance record.
  Archive, installed Core and connected-host qualification remain separate;
  real OS cold-stop, restart and reboot operations require their own delivery.
- Stable remains 1.2.0. Update channels, tags and published assets are unchanged.

See the [beta1 candidate notes](release/1.3.0-beta1/notes.md).

## 1.3.0-alpha6 - source checkpoint

- Internal development identity preceding beta1; this entry does not assert
  publication or completed release qualification.

## 1.3.0-alpha5 - 2026-10-24

### Fixed

- Read Core identity from the owning distribution through shared CoreProperties
  across CLI, Runtime, monitor, MCP and Host.
- Keep the loaded identity immutable and observe installed metadata separately;
  diagnose changed builds and report unknown for missing or inconsistent data.

### Changed

- Record build-aware Core provenance in Runtime/Host state and MCP action
  discovery while retaining separate release, component, protocol and schema
  versions and existing public CLI/MCP parameters and response fields.

See the [alpha5 release notes](release/1.3.0-alpha5/notes.md).

## 1.3.0-alpha4 - 2026-10-23

### Changed

- Separate project initialization, context refresh/repair, context observation and
  search from workplace documentation indexing. Resource mutations mark derived
  state stale; indexing runs through an explicit manual command.
- Route workplace manual indexing, existing scoped CLI refresh/rebuild/tick and
  the cold future-scheduler job through one Core indexing component. Keep SQLite
  FTS5 as the default backend behind a narrow adapter contract.
- Record durable maintenance state and serialize writers with an OS-owned lock,
  preserving explicit interruption recovery and current query/access filters.

### Added

- Add `knowledge-add-batch` with per-item transaction results and one final
  indexing pass limited to successfully added resource IDs; retain unrelated
  documents, read-only dry-run and explicit global reconciliation.
- Add `search-index-maintain --workplace <workplace> --apply [--json]` for explicit
  authorized workplace maintenance. Periodic execution belongs to the future PF
  scheduler; additional database/vector adapters and RAG remain separate work.

### Fixed

- Open index readers without database creation or the default SQLite lock wait,
  preserving live WAL reads and safe unavailable-state reporting.
- Keep context/required-resource readiness independent from search availability;
  redact unknown diagnostics and preserve selected-resource query boundaries.

See the [alpha4 release notes](docs/releases/1.3.0-alpha4.md).

## 1.3.0-alpha3 - 2026-10-22

### Added

- Add explicit SQLite journal maintenance: consistent backup bundles through the
  SQLite backup API, manifest/hash/integrity verification and restoration to a
  new destination. See [journal maintenance](docs/concepts/sqlite-journal-maintenance.md).
- Preserve corrupt legacy journal lines byte for byte in a verifiable quarantine,
  including NUL bytes, with source offsets and hashes. Import refuses invalid
  rows unless `--skip-invalid` is explicit; counts, replay and migration barriers
  remain visible. The existing migration script delegates to the shared service.
- Explain required evidence and accepted evidence shapes in shared Work responses.
  Artifact authoring findings are advisory and retain the reviewed content hash.
- Store available native-worker token usage and execution time in a shared
  accounting store, with CLI inspection/export and explicit partial coverage.

### Changed

- Display monitor calendar uptime in years, months, days, hours and minutes.
- Keep the new maintenance services independent of Main and Host composition;
  CLI adapters compose narrow backup/scanning ports and existing journal owners.

### Fixed

- Accept the supported Kimi native hook and raw-conversation payloads while
  preserving ingress policy and historical evidence bytes.

This cumulative prerelease includes accepted changes after alpha1 and the
qualified alpha2 development archives. See the [alpha3 release notes](docs/releases/1.3.0-alpha3.md).

## 1.3.0-alpha1 - 2026-10-20

### Changed

- Freeze the accepted development checkpoint as the first 1.3.0 alpha while
  preserving public CLI/MCP contracts and file-only operation.
- Continue the accepted internal Core separation across resource readers,
  project context, lifecycle and update owners. Further refactoring remains
  outside this frozen release.
- Provide portable shared Python QA tools and explicit assurance requirements,
  keeping quality dependencies outside the installed Core.
- Configure the supported native Codex hooks during Forge initialization while
  preserving existing user settings.

### Fixed

- Keep official-pack context freshness consistent between CLI and MCP when
  identical text uses LF or CRLF line endings, without refreshing the snapshot.
- Handle disconnected HTTP clients without retrying accepted responses and
  retain the qualified console-free Windows App Server launch.
- Order update prereleases correctly so a later alpha and the final release
  can follow an installed alpha; ignore build metadata for precedence while
  preserving existing resource constraints and channel selection.
- Restore the missing Path import in the focused runtime hardcode-policy smoke.

See the [alpha release notes](docs/releases/1.3.0-alpha1.md). This prerelease
does not replace the stable 1.2.0 channel.

## 1.2.0 - 2026-10-18

### Changed

- Refresh English and Russian user documentation, setup guidance, agent prompts
  and diagrams. Add a shared requirements checklist with Python modules,
  storage needs and app-server memory planning; README badges follow the
  latest published stable release automatically.
- Keep project scratch under `.pf/tmp/`. Add configurable old-file
  notifications from the optional app-server, without automatic deletion.
  See [temporary files](docs/temporary-files.md).
- Store project event and native hook journals in separate local SQLite databases
  with transactional admissions, indexed replay and independent history controls.
  Existing journals require a controlled cutover with the explicit temporary
  migrator; installing Core does not import or delete legacy history. See
  [journal migration](docs/concepts/hook-journal-sqlite.md).
- Remove each Runtime publisher's failed staging file while preserving the
  destination and original error. Host JSON/history share the bounded Windows
  publication writer; the standalone hook installer retains its backup and
  cleans its own unique staging file. No directory scan is added to hooks.
- Separate Runtime operational health from Inspector task outcomes. Failed
  worker attempts and collection recovery remain visible without degrading a
  successful scheduler pass; explicit tick exit codes retain their task meaning.
  Partial metrics coverage remains explicit after successful publication.
- Make automatic Garage hooks opt-in with inherited `runtime.garage_hooks`
  configuration, while Forge retains its required gatekeeper. Native session
  hooks register/check out automatically through Runtime or CLI; first allowed
  hooks cover live opt-in without creating an avoidable deferred message.
  See [hook configuration](docs/concepts/runtime-configuration.md).
- Reuse unchanged safe YAML parsing across requests with bounded, content-keyed
  memory and isolated results. Runtime Run discovery retains only validated
  identity/status fields instead of copying complete histories. Current file
  reads, safe-loader rules and authority checks remain live; see
  [document reads](docs/concepts/document-reads.md).

- Fixed an intermediate checkpoint of the ongoing Core refactoring: concrete
  readers, context/resource policies, lifecycle rules and journal owners serve
  migrated consumers; default bootstrap/composition still includes legacy paths.
- Optimized verified exact Work selection and bounded current-byte journal
  reuse across projects. Full OOP-01 through OOP-05 acceptance remains future work.
- Supervisor observes completed captures as history and stops automatic repeated
  stable semantic collect refusal with a visible recovery reason. Explicit/first
  collection, new attempts and transient-error retry retain their checks.
- Preserved separate release/process/schema/startup-contract versions and
  historical Work pins. See `docs/releases/1.2.0-migration.md`.

### Known qualification limits

- Large retained histories can increase scheduler/admission cost. Qualification
  of source, archive, installed Core and connected host remains distinct;
  publication requires explicit maintainer approval.

### Fixed

- Deferred egress initialization to its CLI callback, preserving parser and
  egress contracts while avoiding unrelated command startup work.
- Corrected diagnostic smoke accounting for bounded best-effort refusal and
  started the thread fixture deadline inside the requesting thread. The
  diagnostics implementation, 50 ms admission budget and exclusion/storage
  checks remain unchanged.


### Changed

- `START_AGENT_HERE.md` is no longer needed. New project onboarding and
  deterministic repair no longer create it; project entry uses root `AGENTS.md`
  and current ProcessForge context instead.
- Existing START files remain untouched, including during forced onboarding
  and repair. A missing START no longer affects project readiness or doctor
  checks. `agent-start-prompt` remains a no-write guidance preview; explicit
  compatibility placement is still available with `--apply`.

## 1.1.0 - 2026-08-31

### Added

- Added read-only MCP session tools for current context, chat transcript, and
  activity facts, with session/project authorization checks.
- Added snapshot-authorized local resource search for project knowledge,
  templates, and resource metadata, including fulltext, metadata-only, and
  non-indexed resource policies.
- Added Runtime support for Codex event capture, replay, projection rebuilding,
  long-lived runtime health checks, and local MCP/search acceptance flows.
- Added manifest-based ProcessForge core update planning, apply, incomplete
  update detection, and repair reporting.
- Added the sessionless Garage entry layer with PF-first context, governed work
  bootstrap, snapshot-authorized search, and resource resolution through MCP.
- Added governed project initialization and repair tools with bounded status and
  explicit mutation guards.
- Added opt-in Windows Task Scheduler autostart for PF Runtime and Codex-owned
  stdio MCP registration lifecycle commands.
- Added Codex hook ingestion for session lifecycle, prompts, assistant stop
  messages, subagent final messages, tool activity, telemetry, and private chat
  projections.

### Changed

- Project initialization now reports bounded initialization status, deterministic
  repair options, and local search readiness instead of relying only on file
  presence.
- Generic project onboarding no longer installs Codex hooks; optional host
  telemetry remains available through an explicit operator action.
- Resource search refresh is maintenance-owned: query calls report missing,
  stale, fresh, or degraded index state, while maintenance ticks perform rebuilds.
- Context freshness and execution readiness are now reported separately, so fresh
  knowledge resources remain searchable when a write/test/browser capability is
  missing.
- Release packaging and archive validation now require clean Git provenance,
  checksum alignment, public-cleanliness gates, and extracted archive tests.
- PF-managed Codex workers now load immutable PF context and authorized
  resources before filesystem discovery, select sandbox mode from assignment
  ownership, and keep inherited host secrets out of durable command state.
- Runtime, MCP, and local search now share one authorized resource resolver so
  Garage and Ledger-bound reads use the same snapshot boundary.

### Fixed

- Fixed stale search-index behavior so changed or damaged resource snapshots do
  not appear fresh.
- Fixed local SQLite/FTS capability handling so unavailable FTS reports degraded
  search readiness instead of leaking uncontrolled exceptions through status
  paths.
- Fixed core-update recovery semantics so locally modified files are not
  overwritten silently and incomplete updates can be classified for repair.
- Fixed stale public distribution artifacts in `dist/` from blocking release
  qualification.
- Fixed Runtime status lock contention and full-journal scans so status remains
  responsive while scheduler jobs are active.
- Fixed Codex MCP tool annotations, explicit Python command drift detection,
  missing-session diagnostics, and bounded PF context responses.
- Fixed derived-report freshness, governed-work duplicate prevention, session
  expiry projections, and project initialization/search recovery diagnostics.

### Internal

- Moved more project initialization, local resource search, core update, process
  catalog, and runtime read logic into `processforge_core` / `tools/pf_runtime`
  modules while keeping CLI and MCP behavior stable.
- Added `ResourceSearchIndex` as the local-search application service used by
  CLI, MCP, and session read adapters.
- Expanded smoke coverage for Runtime, MCP, local search, update manifests,
  freshness/readiness, release provenance, and extracted archive validation.

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
