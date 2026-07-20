# Assignment: Global ProcessForge Update Source Design

Date: 2026-07-20
Run: `pf-global-update-design-20260720`
Task: `task-001-global-update-design-brief`
Status: planning only

## Objective

Design the first update layer for ProcessForge: updating the global ProcessForge distribution installed on a workplace, for example `D:\.agents\process-forge`.

Do not design project `.pf` migration in this task. Project-level update depends on the global distribution already being updated and verified.

## Current ProcessForge Baseline

Current ProcessForge global update support is file-first:

- `self-update-check` reads a local distribution update index.
- Local candidates are `updates/processforge-update-index.yaml` and `updates/channels.yaml`.
- CLI arguments currently are `--distribution-root`, `--current-version`, and `--channel`.
- There is no implemented URL source registry, remote release polling, package download, signature verification, installation, or scheduler/orchestrator notification loop.

Current conceptual documentation states that network update servers and automatic update execution are future integrations.

## Required Future Capability

ProcessForge must support a configured list of update information sources for the global distribution.

Supported source families:

1. Git release providers:
   - GitHub Releases
   - GitVerse or similar Git hosting systems
   - other provider-specific release APIs when added later

2. Generic manifest providers:
   - a custom server returning JSON
   - JSON contains available versions, release metadata, package download links, checksums/signatures, migration guide links, and channel information

The future workplace orchestrator will check sources during startup and/or periodically, then notify the operator when a newer ProcessForge version is available. Automatic install can be separate from discovery and notification.

## Joomla Reference To Study

Use the local Joomla 6.1.0 core mirror as the reference:

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

Observed Joomla mechanics:

- Extension manifests can declare `<updateservers>`.
- A `<server>` has at least `type`, `name`, and URL text; examples include `type="collection"` and `type="extension"`.
- Joomla XML examples include a `priority="1"` attribute on an update server, but the inspected Joomla 6.1.0 extension plugin path does not appear to use that attribute when adding update sites.
- Joomla stores update sites separately from installed extensions and links them through a mapping table.
- Joomla updater only queries enabled update sites.
- Joomla supports collection update sites that can point to additional update sites.
- Joomla update retrieval temporarily disables a site while fetching it, retries by appending `extension.xml` when appropriate, logs failures, and re-enables the site after a successful response.
- Joomla can preserve `extra_query` values when rebuilding update sites, supporting commercial/private download tokens.
- Joomla core update can switch between default and custom update URL and derives update type from URL shape.
- Joomla has a `DownloadSource` object with type, format, and URL for package downloads.

## Design Questions For The Subagent

Answer these without editing code:

1. What should the ProcessForge global update source registry look like?
2. Should source priority be numeric, ordered-list based, or both?
3. How should GitHub/GitVerse-style release providers map into a normalized ProcessForge update manifest?
4. What JSON shape should a custom update server return?
5. What fields are mandatory for safe update discovery and later download/install?
6. How should channels, versions, prerelease/stability, constraints, checksums, signatures, and migration guide links be represented?
7. How should PF handle source failures, duplicate versions from multiple sources, and provider priority?
8. What should the orchestrator persist after checks: cache, last check timestamp, notification state, candidate list?
9. What CLI surface should be added later for discovery, download, and install?
10. What should remain manual/operator-approved at this stage?

## Initial Design Direction

Prefer separating these concerns:

- source registry: where update metadata can be discovered
- normalized update index: provider-independent list of available ProcessForge versions
- candidate cache: results from the last check, including source health
- notification state: which available versions were already reported to the operator
- package cache: downloaded archives and verification metadata
- install transaction: backup, extract, verify, rollback notes

Do not conflate global distribution update with project `.pf` migration.

## Expected Subagent Output

Return a concise but concrete report with:

- recommended data model
- sample YAML source registry
- sample normalized JSON update manifest
- recommended provider behavior for GitHub/GitVerse/custom JSON
- discovery and notification flow
- security and rollback requirements
- minimum CLI commands to add later
- open questions and risks

No code changes.
