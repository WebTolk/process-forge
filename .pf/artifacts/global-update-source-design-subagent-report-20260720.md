# Global ProcessForge Update Source Design: Subagent Report

Date: 2026-07-20
Run: `pf-global-update-design-20260720`
Task: `task-001-global-update-design-brief`
Subagent: `Planck`
Status: planning report; no code changes

## Boundary

Only the first update layer is covered: updating the global ProcessForge distribution, for example `D:\.agents\process-forge`.

Project `.pf` migration is intentionally out of scope and remains the second layer after the global distribution is updated and verified.

## Joomla Reference Findings

Files reviewed by the subagent:

- `D:\.agents\docs\Joomla-core\6.x\6.1.0\administrator\manifests\files\joomla.xml`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\administrator\manifests\packages\pkg_en-GB.xml`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\plugins\extension\joomla\src\Extension\Joomla.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\libraries\src\Updater\Updater.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\libraries\src\Updater\UpdateAdapter.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\libraries\src\Updater\Adapter\CollectionAdapter.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\libraries\src\Updater\Adapter\ExtensionAdapter.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\libraries\src\Updater\DownloadSource.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\libraries\src\Table\UpdateSite.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\administrator\components\com_joomlaupdate\src\Model\UpdateModel.php`
- `D:\.agents\docs\Joomla-core\6.x\6.1.0\administrator\components\com_installer\src\Model\UpdatesitesModel.php`

Findings:

- Joomla manifests declare update servers through `<updateservers><server name type>URL</server>`.
- `pkg_en-GB.xml` has `priority="1"`, but the inspected Joomla 6.1.0 extension plugin path does not use that attribute when adding update sites.
- ProcessForge should define its own explicit priority contract instead of copying Joomla XML semantics.
- Joomla stores update sites separately from installed extensions and links them by mapping.
- Joomla checks only enabled update sites, keeps last check metadata, supports rebuild, and preserves `extra_query`.
- Joomla supports collection update sites that reveal additional update sites.
- Joomla update retrieval disables a site while fetching, retries by appending `extension.xml` where appropriate, logs failures, and re-enables after a successful response.
- Joomla `DownloadSource` models downloads as separate objects with type, format, and URL.
- Discovery, download, verification, and installation should stay separate.

## Recommended Source Registry

Use an ordered source list with numeric priority. Resolution order:

1. enabled sources only
2. lower numeric `priority` first
3. file order as tie-breaker

Example:

```yaml
schema_version: 1
product: processforge
sources:
  - id: github-webtolk-processforge
    name: WebTolk ProcessForge GitHub
    enabled: true
    provider: github_releases
    priority: 10
    owner: WebTolk
    repo: process-forge
    channels: [stable, beta]
    include_prereleases: true
    asset_patterns:
      package: "^processforge-v(?P<version>.+)\\.zip$"
      manifest: "^processforge-v(?P<version>.+)\\.manifest\\.json$"
      signature: "^processforge-v(?P<version>.+)\\.zip\\.(sig|minisig)$"
    auth:
      token_env: GITHUB_TOKEN
    trust:
      require_https: true
      require_sha256: true
      require_signature_for_install: true
      trusted_signers: ["processforge-release"]
    cache_ttl_seconds: 3600

  - id: gitverse-webtolk-processforge
    name: WebTolk ProcessForge GitVerse
    enabled: true
    provider: gitverse_releases
    priority: 20
    owner: WebTolk
    repo: process-forge
    api_base_url: "https://api.gitverse.ru"
    channels: [stable]
    auth:
      token_env: GITVERSE_TOKEN

  - id: custom-processforge-json
    name: Custom ProcessForge Update Server
    enabled: false
    provider: processforge_json
    priority: 30
    url: "https://updates.example.com/processforge/index.json"
    headers_env:
      Authorization: PROCESSFORGE_UPDATE_AUTH
```

Registry should live outside the distribution root so it survives distribution replacement.

## Normalized Manifest

All providers should normalize into one internal manifest shape:

```json
{
  "schema_version": 1,
  "product": { "id": "processforge" },
  "generated_at": "2026-07-20T00:00:00Z",
  "channels": {
    "stable": { "latest": "1.0.1", "minimum_stability": "stable" },
    "beta": { "latest": "1.1.0-beta1", "minimum_stability": "beta" }
  },
  "versions": [
    {
      "version": "1.0.1",
      "channels": ["stable"],
      "stability": "stable",
      "prerelease": false,
      "released_at": "2026-07-20T00:00:00Z",
      "source": { "id": "github-webtolk-processforge", "provider": "github_releases" },
      "release": {
        "tag": "v1.0.1",
        "commit": "sha-or-null",
        "html_url": "https://github.com/WebTolk/process-forge/releases/tag/v1.0.1"
      },
      "constraints": {
        "min_python": "3.11",
        "platforms": ["windows"],
        "min_distribution_schema": 1
      },
      "migration": {
        "project_migration_required": false,
        "guide_url": "https://example.com/processforge/1.0.1/migration.md"
      },
      "artifacts": [
        {
          "type": "full",
          "format": "zip",
          "url": "https://github.com/.../processforge-v1.0.1.zip",
          "size": 1234567,
          "sha256": "hex",
          "signature": {
            "type": "minisign",
            "url": "https://github.com/.../processforge-v1.0.1.zip.minisig",
            "key_id": "processforge-release"
          }
        }
      ]
    }
  ]
}
```

Mandatory for safe discovery:

- `schema_version`
- `product.id`
- source id/provider
- `version`
- at least one channel
- stability/prerelease
- `released_at`
- release identity tag/id
- artifact type/format/url
- constraints sufficient to reject incompatible candidates

Mandatory before download/install:

- `sha256` at minimum
- signature should be required for install once release signing keys are introduced

## Provider Behavior

GitHub/GitVerse release providers:

- fetch release lists, not only "latest", because non-stable channels need prereleases
- skip drafts
- map `tag_name` to semver
- map `prerelease` to stability/channel policy
- collect assets by configured patterns
- require sidecar checksum/manifest when provider asset digest is unavailable

Custom JSON provider:

- should return the normalized manifest directly or a strict subset that PF can normalize
- must not execute logic or override local trust policy

## Merge And Failure Rules

- Duplicate key: same `version + channel`.
- Prefer candidates from higher-priority trusted sources.
- If two sources report the same version but with different artifacts/checksums, mark as `conflict`.
- Conflicted candidates are not installable and should not be presented as a safe update.
- Source failures are recorded per source.
- The entire check fails only when all enabled sources fail or the selected channel has no healthy source.

## Discovery, Cache, And Notification Flow

1. Load source registry from workplace-level storage outside the distribution.
2. Fetch enabled sources by priority with TTL/ETag cache.
3. Normalize provider payloads into one candidate list.
4. Validate schema, semver, channels, constraints, checksum/signature metadata.
5. Persist source health, raw response hash, normalized candidates, and latest selected candidate per channel.
6. Notify the operator only when a newer candidate appears and was not acknowledged or snoozed.
7. Never install during startup discovery.

Suggested persisted state:

- `update-source-cache.json`: per-source status, HTTP status, error, checked_at, ttl, raw_hash
- `update-candidates.json`: normalized candidates and merge/conflict decisions
- `update-notifications.json`: version/channel/source, first_seen_at, last_notified_at, ack/snooze state
- `package-cache/`: downloaded archives, manifests, checksum/signature verification results
- `install-transactions/`: backup path, staged path, selected package, validation log, rollback notes

## Future CLI Surface

```text
pf self-update sources --registry <path> --validate
pf self-update discover --distribution-root D:\.agents\process-forge --channel stable --refresh --json
pf self-update candidates --channel stable
pf self-update download --version 1.0.1 --source github-webtolk-processforge
pf self-update verify --package <zip> --manifest <json>
pf self-update install --package <zip> --distribution-root D:\.agents\process-forge --approve
pf self-update rollback --transaction <id>
pf self-update notify --ack 1.0.1 --channel stable
```

## Operator Approval Boundary

Require explicit operator approval for:

- adding or changing remote sources
- enabling custom/private sources
- switching channel to beta/dev
- downloading from a source with missing checksum/signature
- every install
- every rollback
- every project `.pf` migration after global PF update

## Open Risks

- release signing mechanism is not selected yet
- GitVerse auth/header details should stay provider-configurable
- release asset naming must be standardized
- cache and registry location must be outside `D:\.agents\process-forge`
- Windows in-place replacement needs file lock handling and a side-by-side staged install path
