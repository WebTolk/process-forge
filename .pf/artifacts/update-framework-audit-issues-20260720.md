# Update Framework Audit Issues - 2026-07-20

Scope: current read-only update framework slice after commit `4f896d6`.

This file is a backlog for later fixes. It records only observed gaps, defects,
or contract drift. Absence of provider fetch/download/install/rollback is not
listed as a defect when it matches the intentionally read-only slice boundary.

## UF-AUD-001 - High - `update manifest validate` bypasses the JSON Schema contract

Location:
- `tools/processforge.py:9865` `validate_normalized_update_manifest_data()`
- `schemas/normalized-update-manifest.schema.json`

Observed:
`pf update manifest validate --file <manifest>` uses a hand-written validator
that accepts a version entry without schema-required fields such as `version`,
`channels`, `stability`, `prerelease`, `yanked`, and `source`.

Evidence:
Temporary manifest with `versions: [{ artifacts: [...] }]` returned:
`PASS: ... valid normalized update manifest`.

Impact:
Future discovery/download layers may accept incomplete provider data as
normalized metadata.

Fix direction:
Make the command validate against `normalized-update-manifest.schema.json` and
keep only extra semantic checks in Python.

## UF-AUD-002 - High - Artifact `sha256` is presence-only

Location:
- `tools/processforge.py:9898`
- `schemas/normalized-update-manifest.schema.json`

Observed:
`sha256: not-a-sha` passes `pf update manifest validate`.

Impact:
The future verifier/download layer cannot rely on the manifest validator to
guarantee usable integrity metadata.

Fix direction:
Require lowercase/uppercase 64-character hex for SHA-256 in both schema and
manual semantic checks.

## UF-AUD-003 - High - Artifact URLs are not constrained by trust policy

Location:
- `tools/processforge.py:9896`
- `schemas/normalized-update-manifest.schema.json`

Observed:
Normalized manifests accept artifact URLs such as `http://...`.

Impact:
If discovery later reuses the current validator, insecure artifact URLs can be
promoted to candidates.

Fix direction:
Define artifact URL policy for normalized manifests. Default should reject
non-HTTPS remote URLs unless an explicit local trust policy allows them.

## UF-AUD-004 - Medium - Source URL validation accepts malformed HTTPS URLs

Location:
- `tools/processforge.py:9418`

Observed:
`https:/bad` passes `pf update bootstrap-source validate` because the validator
checks only `urlparse(url).scheme == "https"`.

Impact:
Bad source registries can pass validation and fail later during discovery.

Fix direction:
Require a valid remote URL shape for remote providers: scheme, netloc, and no
control characters. Keep local file handling provider-specific.

## UF-AUD-005 - Medium - `priority` is required by schema but optional in CLI validation

Location:
- `schemas/update-source-registry.schema.json`
- `tools/processforge.py:9385`
- `tools/processforge.py:9474`

Observed:
The schema requires `priority`, but `pf update bootstrap-source validate`
accepts a source without `priority` and sorting silently defaults it to `1000`.

Impact:
Different validators disagree about whether the same registry is valid.

Fix direction:
Choose one contract. Recommended: keep `priority` required for deterministic
operator-visible order, and fail in Python validation when it is missing.

## UF-AUD-006 - Medium - `headers_env` can carry raw header values

Location:
- `tools/processforge.py:9430`
- `schemas/update-source-registry.schema.json`
- `schemas/entity-update-sites.schema.json`

Observed:
`auth.token` is rejected, but `headers_env.Authorization: "Bearer raw-token"`
passes validation.

Impact:
The contract says secrets stay out of manifests, but current validation allows
raw bearer tokens in fields named as environment references.

Fix direction:
Validate `headers_env`, `query_env`, and `custom_headers_env` values as
environment-variable names or replace them with a stricter `secret_ref` model.

## UF-AUD-007 - Medium - `installed-subjects` is declared but not consumed

Location:
- `tools/processforge.py:9319`
- `tools/processforge.py:9548`
- `templates/registries/installed-subjects.yaml`
- `schemas/installed-subjects.schema.json`

Observed:
The registry path and schema exist, and the smoke test asserts it is not
modified, but the entity source builder derives installed subjects only by
live-scanning manifests/registries.

Impact:
The update framework has no authoritative installed-subject inventory yet.
Installed entities that are not discoverable through the current scan model
cannot participate in update checks.

Fix direction:
Decide whether `installed-subjects.yaml` is source-of-truth or future state. If
source-of-truth, make the builder read it and reconcile scanned manifests
against it.

## UF-AUD-008 - Medium - `update-site-overrides.yaml` has no schema validation

Location:
- `templates/registries/update-site-overrides.yaml`
- `tools/processforge.py:9665`
- `tools/validate-process-forge-schemas.py`

Observed:
The file is created and read, but there is no dedicated schema file and no
schema mapping in `validate-process-forge-schemas.py`.

Impact:
Typos in override keys can be silently ignored. Invalid local override state can
survive validation gates.

Fix direction:
Add `schemas/update-site-overrides.schema.json`, validate the template, and add
semantic checks for duplicate `site_id`, supported override keys, and env-ref
fields.

## UF-AUD-009 - Medium - Self-update docs and new update framework docs are not reconciled

Location:
- `docs/concepts/processforge-self-update.md`
- `.pf/artifacts/update-framework-implementation-spec-20260720.md`
- `tools/processforge.py:11400`

Observed:
The self-update concept still says network update servers are future
integrations. The code now has read-only source registries for Git/release/custom
providers, while the old top-level `self-update-check` still reads only the
distribution-local update index.

Impact:
An operator or agent can read conflicting guidance about which update surface is
current.

Fix direction:
Document the current split explicitly: `self-update-check` is local-index only;
`pf update ...` is the read-only registry/manifest surface; network discovery is
not implemented yet.

## UF-AUD-010 - Low - Full generic update CLI is specified but only the read-only subset exists

Location:
- `.pf/artifacts/update-framework-implementation-spec-20260720.md`
- `tools/processforge.py:11399`

Observed:
The spec lists `pf update discover`, `candidates`, `download`, `verify`,
`plan-install`, `install`, `rollback`, and `notify`. Current CLI implements only
`bootstrap-source`, `sources`, `entity-sources`, and `manifest`.

Impact:
This is acceptable for the first slice, but must remain visible so later agents
do not assume the full system exists.

Fix direction:
Add a documented implementation status table and keep future commands out of
operator-facing quickstarts until implemented.

## UF-AUD-011 - Low - Update-site schemas are duplicated across entity schemas

Location:
- `schemas/package-manifest.schema.json`
- `schemas/process-definition.schema.json`
- `schemas/tool-definition.schema.json`
- `schemas/mcp-definition.schema.json`
- `schemas/reusable-template.schema.json`
- `schemas/platform-contract.schema.json`
- `schemas/entity-update-sites.schema.json`

Observed:
Each entity schema carries a local copy of `updateSite`. Field coverage already
differs across files; for example some include `headers_env`, others do not.

Impact:
Update-site contract drift is likely as the updater evolves.

Fix direction:
Introduce one shared update-site schema definition or generate/check copied
definitions with a parity test.

## UF-AUD-012 - Low - `task-create` emits a Python deprecation warning

Location:
- `tools/processforge.py:6770`
- `tools/processforge.py:6771`

Observed:
Creating the audit task printed:
`DeprecationWarning: 'maxsplit' is passed as positional argument`.

Impact:
CLI output is noisy and can confuse scripts that consume command output.

Fix direction:
Change the calls to pass `maxsplit=1` by keyword.
