# ProcessForge Update Framework Audit - 2026-07-20

## Scope

Audited the current read-only update framework surface:

- update source registry schemas and templates
- entity-level `update_sites`
- derived installed update sites
- normalized update manifest validation
- CLI commands under `pf update ...`
- relation to existing `self-update-check`
- smoke coverage

No framework code was changed during the audit.

## Current State

The implemented slice is a useful read-only foundation:

- global bootstrap update sources live in workplace registries
- installed entity manifests can declare update sites
- derived installed update sites can be rebuilt or listed
- normalized manifest fixtures can be checked through CLI
- release-test includes `smoke_update_framework_readonly`

The implementation intentionally does not fetch remote sources, merge
candidates, download packages, install updates, roll back transactions, or
migrate project `.pf` directories.

## Main Findings

The strongest risks are validator drift and trust-boundary weakness:

1. `pf update manifest validate` does not enforce the JSON Schema contract and
   accepts incomplete normalized manifests.
2. Artifact `sha256` values are not checked as 64-character hex digests.
3. Artifact URLs are accepted without HTTPS/trust policy enforcement.
4. Source URL validation accepts malformed HTTPS URLs.
5. `priority` is required by schema but optional in Python validation.
6. `headers_env` can contain raw header values despite the no-raw-secret
   contract.
7. `installed-subjects.yaml` exists as a registry but is not consumed by the
   builder.
8. `update-site-overrides.yaml` has no schema validation.

Full backlog with evidence and fix directions:
`.pf/artifacts/update-framework-audit-issues-20260720.md`.

## Checks Run

- `pf update manifest validate` against intentionally incomplete normalized
  manifest: reproduced false PASS.
- `pf update manifest validate` against invalid `sha256`: reproduced false PASS.
- `pf update manifest validate` against HTTP artifact URL: reproduced PASS.
- `pf update bootstrap-source validate` against malformed `https:/bad` source:
  reproduced false PASS.
- `pf update bootstrap-source validate` against missing `priority`: reproduced
  false PASS against schema expectation.
- `pf update bootstrap-source validate` against raw `auth.token`: correctly
  failed.
- `pf update bootstrap-source validate` against raw-looking `headers_env` value:
  reproduced false PASS.

## Recommended Fix Order

1. Make CLI validators call the corresponding JSON Schemas first, then run
   semantic checks.
2. Tighten URL, SHA-256, and secret-reference validation before implementing any
   network fetch or download command.
3. Add schema validation for `update-site-overrides.yaml`.
4. Decide and implement the role of `installed-subjects.yaml`.
5. Reconcile `self-update-check` docs with the new `pf update ...` read-only
   framework.
6. Add regression smokes for every false PASS listed in the issues log.

## Status

Audit complete. Follow-up work should start from
`.pf/artifacts/update-framework-audit-issues-20260720.md`.
