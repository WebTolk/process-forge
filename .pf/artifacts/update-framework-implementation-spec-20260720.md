# ProcessForge Update Framework Implementation Specification

Date: 2026-07-20
Run: `pf-update-implementation-spec-20260720`
Task: `task-001-update-framework-spec`
Status: implementation-ready planning; no code changes

## 1. Purpose

ProcessForge needs a generic update framework for the global workplace layer.

The framework must discover, validate, cache, notify, download, verify, and install updates for typed ProcessForge subjects:

- ProcessForge distribution
- knowledge packages
- knowledge resources and local documentation mirrors
- process definitions
- reusable templates
- tool registrations
- MCP server registrations
- platform composition contracts
- aggregate packages that group any of the above

Project `.pf` migration remains a later second layer and must not be performed by startup update discovery.

## 1.1. Design Position

The goal is a ProcessForge-native update system that solves two practical problems on a workstation:

1. obtain trustworthy information about available updates
2. safely apply approved updates to the global ProcessForge distribution and global ProcessForge-managed entities

## 2. Design Principles

- Update metadata is declared at the level that owns the update decision.
- Global bootstrap sources are workplace policy.
- Installed entities declare their own update sources in their manifests.
- Runtime update checks use derived/cacheable state and do not need to reparse every installed manifest for every operation.
- Discovery, notification, download, verification, installation, and rollback are separate phases.
- Startup and periodic checks never install anything automatically.
- Remote manifests cannot add trusted sources, trusted keys, or approval policy by themselves.
- Private auth, tokens, query strings, and custom headers stay outside public manifests.
- Installed state records exact selected versions, source ids, artifact URLs, hashes, and verification results.
- Every install plan must be deterministic from local state and verified artifacts.
- Every artifact in an install plan must have a required hash before installation.
- Signatures are modeled in the data contract from the start and can become mandatory by local policy.
- Yanked, revoked, incompatible, or conflicted candidates are not installable by default.
- Operator approval is required before changing the global distribution, executable tool registrations, MCP registrations, platform contracts, or project-local `.pf`.

## 4. Scope Boundaries

### In Scope

- global source registry
- provider adapters
- normalized update manifest
- candidate discovery and merge logic
- source health cache
- candidate cache
- notification state
- package download cache
- checksum/signature verification
- subject-specific install planning
- operator approval boundary
- rollback transaction records
- CLI and test design

### Out Of Scope For This Specification

- automatic project `.pf` migration
- unattended installation
- UI implementation
- long-running scheduler implementation details
- remote server implementation
- actual GitHub/GitVerse authentication setup

## 5. Storage Layout

All mutable update framework state must live outside the replaceable ProcessForge distribution root.

Recommended workplace layout:

```text
<PF_WORKPLACE>/
  registries/
    update-sources.yaml
    installed-subjects.yaml
  runtime/
    update/
      source-cache/
        <source-id>.json
      candidates/
        update-candidates.json
        conflicts.json
      notifications/
        update-notifications.json
      package-cache/
        <subject-type>/
          <subject-id>/
            <version>/
              artifact.zip
              artifact.manifest.json
              artifact.sha256
              artifact.sig
              verify.json
      install-transactions/
        <transaction-id>/
          plan.json
          backup.json
          verify.json
          install.log
          rollback.md
```

Distribution root remains replaceable:

```text
<PF_DISTRIBUTION>/
  bin/
  tools/
  docs/
  updates/
```

The distribution may ship default source templates, but active mutable registries live in the workplace.

## 5.1. Source Ownership Model

ProcessForge update sources have two ownership layers.

### Layer A: Global bootstrap sources

Global URLs are configured by the human or agent during primary workplace setup.

These sources are workplace policy. They are used for:

- global ProcessForge distribution updates
- global process flow/bootstrap updates
- optional catalogs for discovering installable entities that are not installed yet
- emergency/offline indexes

They must live outside the replaceable distribution root, for example in `<PF_WORKPLACE>/registries/update-sources.yaml`.

Primary setup must allow the operator or setup agent to provide one or more global update URLs. These URLs answer the question:

```text
Where does this workplace learn about ProcessForge/process-flow updates?
```

They do not need to answer:

```text
Where does every installed knowledge package, template, process, tool, MCP server, or platform contract update from?
```

### Layer B: Entity-owned update sites

Update URLs for concrete entities must live in the installed entity manifests.

This applies to:

- knowledge packages
- knowledge resources when they have independent upstream snapshots
- process definitions
- reusable templates
- tool registrations
- MCP server registrations
- platform composition contracts
- aggregate packages

An installed entity's manifest is the source of truth for that entity's own update sites. The updater may rebuild a derived registry of installed entity update sites by scanning installed manifests, but it must not treat the global source registry as the permanent list of every entity update URL.

Entity manifests answer the question:

```text
Where does this specific installed entity learn about its own updates?
```

### Consequence

`update-sources.yaml` is not a universal catalog of all entity update sources.

It is a bootstrap and policy registry. Entity-specific update sources are declared by the entity/package manifests after installation.

The runtime model is:

- manifests declare entity update sources
- the system stores derived update source records for runtime checks
- rebuild can rescan installed manifests and regenerate derived update source records
- private query/auth material is preserved outside public manifests

Use PF terminology in user-facing CLI: `update_source`, `entity_update_source`, and `candidate`.

## 6. Update Source Registry

File: `<PF_WORKPLACE>/registries/update-sources.yaml`

Purpose: declares global bootstrap update sources for the workplace.

It is not the canonical home for update URLs of already installed entities.

Resolution order:

1. `enabled: true`
2. lower numeric `priority`
3. file order as tie-breaker

Remote manifests cannot mutate this registry automatically.

```yaml
schema_version: 1
product: processforge
updated_at: "2026-07-20T00:00:00Z"

defaults:
  channel: stable
  cache_ttl_seconds: 3600
  require_https: true
  require_sha256_for_download: true
  require_sha256_for_install: true
  require_signature_for_install: false

sources:
  - id: official-github
    name: Official GitHub Releases
    enabled: true
    provider: github_releases
    priority: 10
    owner: ExampleOrg
    repo: process-forge
    channels: [stable, beta]
    include_prereleases: true
    subjects:
      - type: processforge_distribution
        ids: [processforge]
    asset_patterns:
      package: "^processforge-v(?P<version>.+)\\.zip$"
      manifest: "^processforge-v(?P<version>.+)\\.manifest\\.json$"
      checksum: "^processforge-v(?P<version>.+)\\.zip\\.sha256$"
      signature: "^processforge-v(?P<version>.+)\\.zip\\.(sig|minisig|asc)$"
    auth:
      token_env: GITHUB_TOKEN
    trust:
      require_https: true
      require_sha256_for_install: true
      require_signature_for_install: false
      trusted_signers: []

  - id: official-bootstrap-catalog
    name: Official Bootstrap Catalog
    enabled: true
    provider: processforge_json
    priority: 20
    url: "https://updates.example.com/processforge/catalog.json"
    channels: [stable]
    subjects:
      - type: processforge_distribution
        ids: [processforge]
      - type: knowledge_package
        ids: ["*"]
      - type: knowledge_resource
        ids: ["*"]
      - type: process_definition
        ids: ["*"]
      - type: template
        ids: ["*"]
      - type: tool
        ids: ["*"]
      - type: mcp_server
        ids: ["*"]
      - type: platform_contract
        ids: ["*"]
      - type: package
        ids: ["*"]
    headers_env:
      Authorization: PROCESSFORGE_UPDATE_AUTH

  - id: local-emergency-index
    name: Local Emergency Index
    enabled: false
    provider: processforge_json_file
    priority: 90
    path: "D:/updates/processforge/entities.json"
    channels: [stable]
    subjects:
      - type: "*"
        ids: ["*"]
```

### Provider Types

MVP providers:

- `processforge_json`
- `processforge_json_file`
- `github_releases`
- `gitverse_releases`

Later providers:

- `gitlab_releases`
- `generic_http_directory`
- `tuf_repository`

The global bootstrap catalog may advertise installable entities. Once an entity is installed, its own manifest-level update sites take precedence for future updates of that entity.

## 6.1. Entity Manifest Update Sites

Each updatable entity manifest should support top-level `update_sites`.

Recommended shape:

```yaml
update_sites:
  - id: official
    name: Official updates
    enabled: true
    type: processforge_json
    priority: 10
    url: "https://updates.example.com/processforge/entities/docs.example.json"
    channels: [stable]
    trust:
      require_https: true
      require_sha256_for_install: true
      require_signature_for_install: false

  - id: github
    name: Git release updates
    enabled: false
    type: github_releases
    priority: 20
    owner: ExampleOrg
    repo: docs.example
    channels: [stable, beta]
    include_prereleases: true
    asset_patterns:
      package: "^docs.example-v(?P<version>.+)\\.zip$"
      manifest: "^docs.example-v(?P<version>.+)\\.manifest\\.json$"
      checksum: "^docs.example-v(?P<version>.+)\\.zip\\.sha256$"
```

Required fields:

- `id`
- `type`
- `enabled`
- source location fields appropriate for the type

Recommended fields:

- `name`
- `priority`
- `channels`
- `trust`
- `auth_ref` or environment-variable based auth settings

Remote manifests must not carry raw secrets. They may name an `auth_ref` or token environment variable, but the actual secret stays in the workplace secret/config layer.

## 6.2. Derived Installed Entity Update Site Registry

The updater should build a derived runtime registry from installed manifests.

File:

```text
<PF_WORKPLACE>/runtime/update/installed-update-sites.json
```

Suggested shape:

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-20T00:00:00Z",
  "sites": [
    {
      "site_id": "knowledge_package:docs.example:official",
      "subject": {
        "type": "knowledge_package",
        "id": "docs.example",
        "scope": "global",
        "installed_version": "1.1.0"
      },
      "source": {
        "id": "official",
        "type": "processforge_json",
        "priority": 10,
        "url": "https://updates.example.com/processforge/entities/docs.example.json",
        "channels": ["stable"]
      },
      "manifest_path": "D:/.agents/pf-workplace/packages/docs.example/package.yaml",
      "enabled": true,
      "preserved_local": {
        "auth_ref": "updates.docs.example"
      }
    }
  ]
}
```

This file is derived and may be rebuilt.

Persistent operator edits such as disabled state, auth settings, custom headers, custom query strings, or channel override should live in a separate override file:

```text
<PF_WORKPLACE>/registries/update-site-overrides.yaml
```

Rebuild rules:

1. scan installed subject manifests
2. read top-level `update_sites`
3. merge local overrides by stable key
4. preserve auth/custom query equivalents
5. remove update sites for uninstalled subjects
6. do not fetch remote sources during rebuild

Stable key:

```text
subject.type + subject.id + update_site.id
```

## 6.3. Manifest Placement By Subject

Recommended field placement:

### Knowledge package

```yaml
schema_version: 1
id: docs.example
version: 1.2.0
kind: documentation
scope: global
update_sites: []
resources: []
```

### Knowledge resource

Resource-level updates can use existing `source` and `update_policy`, but independent update URLs should be explicit:

```yaml
resources:
  - id: api-docs
    kind: local_mirror
    source:
      url: "https://example.com/docs"
    update_policy:
      cadence: manual
      update_sites:
        - id: upstream-snapshot
          type: processforge_json
          url: "https://updates.example.com/processforge/resources/api-docs.json"
```

### Process definition

```yaml
schema_version: 1
id: software-feature-development
version: 1.0.0
status: active
update_sites: []
```

### Reusable template

```yaml
schema_version: 1
id: project-onboarding-template
version: 1.0.0
source_package: process-forge-core
update_sites: []
```

### Tool definition

```yaml
id: phpunit
capability: test_running
status: configured
update_sites: []
```

Tool update sites update PF tool registration metadata. Installing or updating the executable itself is a separate approved action.

### MCP definition

```yaml
id: playwright
capability: browser_automation
status: configured
update_sites: []
```

MCP update sites update registration metadata. Enabling or changing command/args/env/capabilities requires explicit operator approval.

### Platform contract

```yaml
schema_version: 1
id: platform.example-stack
type: platform_contract
version: 1.0.0
update_sites: []
```

### Aggregate package

Aggregate packages may define their own package update sites. They can also contain subjects that each define their own update sites.

Package-level updates should update the package composition. Subject-level updates should update a specific included subject.

## 7. Normalized Manifest

All providers normalize into the same internal shape.

File shape returned by `processforge_json` may already match this shape.

```json
{
  "schema_version": 1,
  "product": { "id": "processforge" },
  "generated_at": "2026-07-20T00:00:00Z",
  "channels": {
    "stable": { "minimum_stability": "stable" },
    "beta": { "minimum_stability": "beta" }
  },
  "subjects": [
    {
      "type": "knowledge_package",
      "id": "docs.example",
      "name": "Example documentation package",
      "versions": [
        {
          "version": "1.2.0",
          "channels": ["stable"],
          "stability": "stable",
          "prerelease": false,
          "released_at": "2026-07-20T00:00:00Z",
          "yanked": false,
          "source": {
            "id": "knowledge_package:docs.example:official",
            "provider": "processforge_json"
          },
          "release": {
            "tag": "docs.example-v1.2.0",
            "commit": null,
            "html_url": "https://updates.example.com/processforge/docs.example/1.2.0"
          },
          "compatibility": {
            "min_processforge": "1.0.0",
            "max_processforge": null,
            "min_schema": 1,
            "max_schema": 1,
            "platforms": ["windows", "linux", "macos"]
          },
          "dependencies": [
            {
              "type": "knowledge_package",
              "id": "docs.parent",
              "constraint": "^1.0",
              "optional": false
            }
          ],
          "artifacts": [
            {
              "type": "full",
              "format": "zip",
              "url": "https://updates.example.com/processforge/entities/docs.example-1.2.0.zip",
              "size": 1234567,
              "sha256": "hex",
              "signature": {
                "type": "minisign",
                "url": "https://updates.example.com/processforge/entities/docs.example-1.2.0.zip.minisig",
                "key_id": "processforge-release"
              },
              "provenance_url": "https://updates.example.com/processforge/entities/docs.example-1.2.0.provenance.json"
            }
          ],
          "changes": [
            {
              "type": "content",
              "summary": "Updated documentation snapshot.",
              "breaking": false
            }
          ],
          "migration": {
            "required": false,
            "guide_url": null
          }
        }
      ]
    }
  ]
}
```

## 8. Candidate Identity And Selection

Candidate key:

```text
subject.type + subject.id + channel + version + source.id
```

Duplicate key for merge:

```text
subject.type + subject.id + channel + version
```

Selection rules:

1. ignore disabled sources
2. ignore candidates outside the requested subject filter
3. reject invalid schema
4. reject incompatible ProcessForge/schema/platform constraints
5. reject prerelease candidates unless channel/source policy permits them
6. treat `yanked: true` as not selectable by default
7. prefer non-conflicted candidates from higher-priority sources
8. if same version has different artifact URL/checksum/signature from different sources, mark `conflict`
9. if multiple valid versions remain, select highest semantic version for the channel
10. never install during discovery

Conflict candidates may be displayed for operator review but are not installable.

## 9. Installed Subjects State

File: `<PF_WORKPLACE>/registries/installed-subjects.yaml`

Purpose: lock-like global installed state.

```yaml
schema_version: 1
updated_at: "2026-07-20T00:00:00Z"

subjects:
  - type: processforge_distribution
    id: processforge
    scope: global
    version: "1.0.0"
    source_id: local-install
    installed_at: "2026-07-20T00:00:00Z"
    artifact:
      url: "file:///D:/Dev/process-forge/dist/processforge-v1.0.0.zip"
      sha256: "hex"
    install_path: "D:/.agents/process-forge"
    verification:
      version_check: passed
      doctor_workplace: passed

  - type: knowledge_package
    id: docs.example
    scope: global
    version: "1.1.0"
    source_id: "knowledge_package:docs.example:official"
    installed_at: "2026-07-20T00:00:00Z"
    artifact:
      url: "https://updates.example.com/processforge/entities/docs.example-1.1.0.zip"
      sha256: "hex"
    install_path: "D:/.agents/pf-workplace/packages/docs.example"
```

This file records exact selected versions and artifacts. It is not a dependency solver input from remote sources; it is local truth.

## 10. Source Cache

File: `<PF_WORKPLACE>/runtime/update/source-cache/<source-cache-key>.json`

`source_id` is the logical source or update site id. `source-cache-key` must be filesystem-safe on Windows and can be derived from a slug plus hash of the logical id.

```json
{
  "schema_version": 1,
  "source_id": "knowledge_package:docs.example:official",
  "source_cache_key": "knowledge-package-docs-example-official-3f7a9c2e",
  "checked_at": "2026-07-20T00:00:00Z",
  "ttl_seconds": 3600,
  "status": "ok",
  "http": {
    "status": 200,
    "etag": "\"abc\"",
    "last_modified": "Mon, 20 Jul 2026 00:00:00 GMT"
  },
  "raw_hash": "sha256:hex",
  "normalized_subject_count": 8,
  "error": null
}
```

Status values:

- `ok`
- `stale_ok`
- `disabled`
- `unreachable`
- `auth_failed`
- `schema_invalid`
- `provider_error`

## 11. Candidate Cache

File: `<PF_WORKPLACE>/runtime/update/candidates/update-candidates.json`

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-20T00:00:00Z",
  "channel": "stable",
  "candidates": [
    {
      "subject": { "type": "knowledge_package", "id": "docs.example", "scope": "global" },
      "current_version": "1.1.0",
      "available_version": "1.2.0",
      "source_id": "knowledge_package:docs.example:official",
      "status": "available",
      "installable": true,
      "reason": null,
      "artifact_sha256": "hex",
      "migration_required": false
    }
  ],
  "conflicts": []
}
```

Candidate statuses:

- `available`
- `current`
- `incompatible`
- `yanked`
- `conflict`
- `missing_required_hash`
- `missing_required_signature`
- `source_failed`

## 12. Notification State

File: `<PF_WORKPLACE>/runtime/update/notifications/update-notifications.json`

```json
{
  "schema_version": 1,
  "notifications": [
    {
      "subject": { "type": "processforge_distribution", "id": "processforge", "scope": "global" },
      "channel": "stable",
      "version": "1.0.1",
      "source_id": "official-github",
      "first_seen_at": "2026-07-20T00:00:00Z",
      "last_notified_at": "2026-07-20T00:00:00Z",
      "status": "new",
      "acknowledged_at": null,
      "snoozed_until": null
    }
  ]
}
```

Notification statuses:

- `new`
- `notified`
- `acknowledged`
- `snoozed`
- `superseded`
- `withdrawn`

The orchestrator may notify on startup or schedule, but may not install.

## 13. Install Transaction

File: `<PF_WORKPLACE>/runtime/update/install-transactions/<transaction-id>/plan.json`

```json
{
  "schema_version": 1,
  "transaction_id": "update-20260720T000000Z-processforge-1.0.1",
  "created_at": "2026-07-20T00:00:00Z",
  "operator_approved": true,
  "subject": { "type": "processforge_distribution", "id": "processforge", "scope": "global" },
  "from_version": "1.0.0",
  "to_version": "1.0.1",
  "source_id": "official-github",
  "artifacts": [
    {
      "url": "https://github.com/.../processforge-v1.0.1.zip",
      "local_path": "D:/.agents/pf-workplace/runtime/update/package-cache/processforge_distribution/processforge/1.0.1/processforge-v1.0.1.zip",
      "sha256": "hex",
      "verified": true
    }
  ],
  "steps": [
    "backup",
    "stage",
    "verify_stage",
    "activate",
    "post_verify",
    "record_installed_state"
  ],
  "rollback": {
    "available": true,
    "backup_path": "D:/.agents/process-forge.backup-20260720-000000"
  }
}
```

Transaction statuses:

- `planned`
- `downloaded`
- `verified`
- `approved`
- `installing`
- `installed`
- `failed`
- `rolled_back`

## 14. State Machine

Discovery:

```text
idle
  -> sources_loaded
  -> source_fetching
  -> source_normalized
  -> candidates_merged
  -> notifications_updated
  -> done
```

Download:

```text
candidate_selected
  -> download_started
  -> download_complete
  -> hash_verified
  -> signature_verified_or_policy_allows_missing
  -> package_cached
```

Install:

```text
install_plan_created
  -> operator_approved
  -> backup_created
  -> staged
  -> staged_verified
  -> activated
  -> post_verified
  -> installed_state_recorded
```

Failure path:

```text
any_install_step_failed
  -> activation_state_checked
  -> rollback_if_needed
  -> transaction_failed
  -> operator_notified
```

## 14.1. Operational Flows

### Primary workplace setup

1. Operator or setup agent initializes the workplace.
2. Setup asks for global update URLs or uses shipped defaults.
3. URLs are written to the workplace global update registry outside the distribution root.
4. Setup validates source syntax and trust policy.
5. Setup performs optional discovery for `processforge_distribution`.
6. Setup does not download or install updates unless explicitly approved.

### Startup or periodic check

1. Load global bootstrap sources.
2. Discover ProcessForge/process-flow updates from global sources.
3. Rebuild or read derived entity update sources from installed manifests.
4. Discover updates for installed entities from their own declared sources.
5. Merge candidates and detect conflicts.
6. Update notification state.
7. Notify operator.
8. Stop without downloading or installing.

### Approved global ProcessForge update

1. Operator selects a `processforge_distribution` candidate.
2. PF downloads the package to workplace package cache.
3. PF verifies hash/signature according to local policy.
4. PF creates an install transaction and backup.
5. PF stages the new distribution.
6. PF activates it.
7. PF runs post-install checks.
8. PF records installed state.
9. PF leaves project `.pf` untouched.

### Approved entity update

1. Operator selects an entity candidate.
2. PF downloads and verifies the entity artifact.
3. PF builds a subject-specific install plan.
4. PF applies the update only after approval.
5. PF records installed subject state.
6. PF rebuilds derived entity update sources if the updated manifest changed its update URLs.

## 15. Provider Contracts

### `processforge_json`

Input:

- URL
- optional headers from environment variables
- optional ETag/Last-Modified cache

Output:

- normalized manifest or strict compatible subset

Rules:

- HTTPS required unless source explicitly allows local/insecure and operator approved it
- remote manifest cannot add trusted keys
- remote manifest cannot enable new sources
- remote manifest cannot override local approval policy

### `processforge_json_file`

Input:

- local path

Rules:

- intended for emergency/offline use
- disabled by default
- operator must explicitly enable it

### `github_releases`

Input:

- owner
- repo
- asset patterns
- optional token env

Rules:

- use release list, not only latest, so prerelease channels are visible
- skip drafts
- map tag names to semantic versions
- map GitHub `prerelease` to channel/stability policy
- collect archive, manifest, checksum, signature sidecars by asset pattern
- require sidecar checksum if provider metadata does not provide usable digest

### `gitverse_releases`

Input:

- owner
- repo
- API base URL
- asset patterns
- optional token env

Rules:

- behavior follows the same rules as `github_releases`
- auth/header details remain provider-configurable
- sidecar checksum/manifest should be required when asset digest is unavailable

## 16. Security Policy

Default MVP policy:

- HTTPS required for remote sources
- SHA-256 required before install
- missing hash means candidate is not installable
- signature support should be modeled from day one, but may be optional until release signing is implemented
- all executable changes require operator approval
- remote sources cannot write local policy
- cache does not imply trust
- yanked/revoked candidates are not selected by default
- conflicts are not installable

Future hardening:

- required signatures for official distribution updates
- trusted public keys stored in workplace registry
- optional TUF-like metadata for key rotation and expiry
- provenance records for artifacts

## 17. Subject Install Planners

### `processforge_distribution`

Plan:

1. download archive
2. verify hash/signature
3. extract to staging directory
4. run version check in staging
5. optionally run archive/release validation if shipped
6. backup current distribution root
7. activate staged distribution
8. run `version`
9. run `doctor-workplace`
10. record installed state

Rollback:

- restore previous distribution root from backup
- keep failed transaction logs

### `knowledge_package`

Plan:

1. verify artifact
2. validate package manifest
3. resolve dependencies
4. install side-by-side or replace package root according to package policy
5. preserve provenance and local overrides
6. refresh knowledge index
7. record installed state

Rules:

- project overrides are not overwritten
- local mirrors may be full archive in MVP
- incremental mirror update can be later

### `knowledge_resource`

Plan:

1. fetch/update single resource snapshot
2. record source URL/API identity
3. record fetched_at and checksum
4. update parent package index if required

Rules:

- stale notification can happen without install
- license/usage metadata should be preserved

### `process_definition`

Plan:

1. validate process schema
2. compare stages and contracts
3. mark breaking changes when stages are removed/renamed/reordered
4. install side-by-side by version
5. keep active runs pinned to previous definition unless operator migrates them

### `template`

Plan:

1. validate template manifest/schema
2. install updated template source
3. do not modify files already copied into projects

### `tool`

Plan:

1. update tool registration metadata
2. validate command path policy and version detection command
3. do not install third-party executable without explicit approval

### `mcp_server`

Plan:

1. validate registration metadata
2. compare command/args/env/capabilities/approval policy
3. require operator approval for enabling/changing
4. keep secrets outside manifests

### `platform_contract`

Plan:

1. validate contract
2. resolve composition dependencies
3. check compatibility with installed knowledge/tools/templates/MCP/processes
4. install/update global available contract
5. do not change project platform selection

### `package`

Plan:

1. resolve grouped subject updates
2. produce install plan with all included changes
3. verify every artifact
4. apply in dependency order
5. recover from partial failure or leave old versions active

## 18. CLI Specification

Prefer generic `pf update ...`.

`self-update` remains a compatibility alias for:

```text
pf update ... --subject-type processforge_distribution --subject processforge
```

Commands:

```text
pf update bootstrap-source add --workplace <path> --url <url> --provider processforge_json --priority 10
pf update bootstrap-source list --workplace <path>
pf update bootstrap-source validate --workplace <path>
pf update sources --workplace <path> --validate
pf update sources --workplace <path> --list
pf update entity-sources rebuild --workplace <path>
pf update entity-sources list --workplace <path> --subject-type all
pf update discover --workplace <path> --scope global --subject-type all --channel stable
pf update discover --workplace <path> --scope global --subject-type knowledge_package --refresh --json
pf update candidates --workplace <path> --subject-type all --channel stable
pf update candidates --workplace <path> --subject-type processforge_distribution --subject processforge
pf update download --workplace <path> --subject-type knowledge_package --subject docs.example --version 1.2.0
pf update verify --workplace <path> --package <path>
pf update plan-install --workplace <path> --subject-type processforge_distribution --subject processforge --version 1.0.1
pf update install --workplace <path> --transaction <id> --approve
pf update rollback --workplace <path> --transaction <id> --approve
pf update notify --workplace <path> --ack --subject-type template --subject template.project-onboarding --version 1.1.0
```

Compatibility commands:

```text
pf self-update-check
pf self-update-discover
pf self-update-download
pf self-update-install
```

Compatibility commands should call the generic update engine internally.

## 19. Orchestrator Behavior

Startup check:

1. load update registry
2. use TTL cache unless forced
3. discover candidates
4. update notification state
5. show new/superseded/conflict notifications
6. stop

Periodic check:

1. same as startup check
2. obey source TTL
3. avoid repeated notifications if acked/snoozed

Never during startup or periodic check:

- download packages automatically
- install packages automatically
- change MCP/tool enablement
- change project `.pf`

## 20. Test Matrix

### Schema Tests

- valid update source registry
- invalid provider type
- missing source id
- duplicate source id
- invalid subject type
- invalid normalized manifest
- missing artifact hash
- yanked candidate

### Provider Tests

- `processforge_json` valid response
- `processforge_json` schema invalid
- `processforge_json` HTTP 404
- `processforge_json` auth failure
- `processforge_json_file` local file
- GitHub-like fixture with stable release
- GitHub-like fixture with prerelease
- GitHub-like fixture with draft release skipped
- GitVerse-like fixture with asset sidecars
- primary setup stores global bootstrap source URL outside distribution root
- installed entity manifest declares its own update source
- derived installed entity update source registry rebuilds from installed manifests
- local overrides preserve disabled/auth/channel settings across rebuild

### Merge Tests

- same candidate from two sources, same checksum
- same candidate from two sources, different checksum conflict
- higher-priority source wins
- source failure does not hide lower-priority healthy source
- all sources fail
- selected channel has no healthy candidates

### Security Tests

- missing SHA-256 blocks install
- hash mismatch blocks install
- signature required but missing blocks install
- yanked candidate is not selected
- insecure HTTP source rejected by default
- remote manifest cannot add trusted signer

### Notification Tests

- new update notification created
- repeated discovery does not duplicate notification
- ack suppresses repeated notification
- snooze suppresses until time
- superseded update marks older notification superseded
- conflict notification is visible but not installable

### Install Planner Tests

- distribution install plan
- distribution rollback plan
- knowledge package dependency plan
- process definition breaking change plan
- template update plan does not touch copied project files
- tool update requires approval
- MCP update requires approval
- platform contract dependency graph plan
- package grouped update plan

### Windows Tests

- staged extraction path
- backup path collision handling
- locked file failure
- rollback after activation failure

## 21. Implementation Slices

Recommended order:

1. schemas and validators
2. storage path helpers and workplace registry files
3. global bootstrap source registry commands
4. entity manifest `update_sites` schema support
5. derived installed entity update source registry rebuild
6. normalized candidate model
7. `processforge_json_file` provider for deterministic tests
8. `processforge_json` provider
9. candidate merge and conflict detection
10. source/candidate/notification cache
11. CLI read-only commands: `sources`, `entity-sources`, `discover`, `candidates`
12. download and hash verification
13. install planner data model without applying changes
14. distribution install planner and transaction logs
15. subject planners for knowledge packages/templates/processes
16. GitHub/GitVerse providers
17. compatibility `self-update` aliases
18. orchestrator startup/periodic notification integration

## 22. Acceptance Criteria

The implementation is ready when:

- source registry schema exists and validates
- normalized manifest schema exists and validates
- installed subjects state schema exists and validates
- update discovery works from local JSON fixture
- update discovery works from custom HTTP JSON fixture
- candidates are typed by subject
- conflicts are detected and not installable
- missing hashes block install
- notification state is persisted
- `pf update discover` does not modify installed subjects
- distribution install plan can be generated without applying
- distribution install requires explicit approval
- global distribution update does not modify project `.pf`
- tests cover provider failures, conflicts, hashes, yanked candidates, and notification ack/snooze

## 23. Open Decisions

- choose first signature mechanism: minisign, GPG, Sigstore/cosign, or TUF-like metadata
- decide whether official distribution install requires signature immediately or after key bootstrap
- decide exact naming convention for release assets
- decide if entity packages use zip only in MVP
- decide whether package updates support partial application in MVP or require atomic grouped install
- decide exact workplace default paths for update cache and registries
- decide if `self-update-check` remains as-is or becomes a thin alias immediately

## 24. Non-Goals

- do not turn ProcessForge into a general-purpose language package manager
- do not execute remote package scripts
- do not allow remote manifests to modify local trust policy
- do not auto-install at startup
- do not rewrite project `.pf` during global discovery
