# Release Launcher Lifecycle Review

Assignment: `project-init-local-search-mcp-release-launcher-lifecycle-review-20260821`

## Verdict

PASS with a scoped evidence limitation.

The remediation in `tools/processforge.py` preserves the linked-project hard failure, bounds the ProcessForge distribution exception to the missing runtime launcher case, and keeps release cleanup before `doctor-project` in the `release-test` lifecycle.

## Review Scope

Read:
- `tools/processforge.py`
- `.pf/reviews/project-init-local-search-mcp-release-launcher-lifecycle-audit-20260821.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/*`

No product code was edited. I did not run mutating lifecycle commands because `clean --release` removes `.pf/runtime/`, which is outside this worker's allowed write scope.

## Findings

No blocking findings.

## Confirmations

### Ordinary linked projects still hard-fail

Confirmed.

In `command_doctor_project`, missing `.pf/runtime/bin/pf.py` still produces `FAIL` for non-auto, non-distribution projects with the linked-project rationale:

- missing launcher branch: `tools/processforge.py:20287-20315`
- hard-failure hint: linked projects need the local Python launcher because they do not contain ProcessForge core tools.

`auto_workplace_mode` remains a separate existing warning path and is not treated as an ordinary linked-project case.

### Distribution exception is bounded

Confirmed.

The downgrade from `FAIL` to `WARN` applies only when:

- the missing file is specifically `runtime/bin/pf.py`; and
- `looks_like_processforge_distribution(project_root)` is true.

The distribution predicate requires all of these to exist under the project root:

- `bin/pf.py`
- `tools/processforge.py`
- `schemas/process-definition.schema.json`
- `processes/core`

Additionally, `doctor-project` still emits a separate `FAIL` when a root looks like a ProcessForge distribution but the manifest type is not explicitly one of the ProcessForge core/development project types. This prevents the launcher warning from silently blessing a generic project rooted at a distribution checkout.

### Release cleanup remains before doctor

Confirmed by code.

`release_test_commands()` still inserts `clean release artifacts` near the beginning when cleanup is enabled, while `doctor-project` remains near the end of the standard release command list. `safe_remove_generated_path()` still treats `.pf/runtime` as generated release state and removes it during release cleanup.

This means the lifecycle that originally exposed the issue is preserved:

1. `clean --release` removes `.pf/runtime/`;
2. later `doctor-project` runs;
3. missing `.pf/runtime/bin/pf.py` is now a warning only for self-contained ProcessForge distribution roots.

## Evidence Limitation

I could not verify the live latest `.pf/runtime/release-test` report because `.pf/runtime` is outside this worker's allowed read scope, and I did not run the destructive `clean release artifacts` lifecycle check.

The available artifacts do show related remediation evidence:
- Windows cleanup retry was implemented and verified with `python bin/pf.py clean --root . --release`.
- Release smoke registration reports targeted `smoke_project_init_local_search_mcp` and `smoke_project_init_acceptance` as PASS.
- The prior audit precisely documented the original cleanup-to-doctor failure mode and the intended smallest safe remediation.

## Residual Risk

Low.

The review confirms the product-code control flow. The only remaining gap is live runtime proof of the exact combined command sequence in this worker scope. A later orchestrator or release worker with `.pf/runtime` access should capture:

```text
python tools/processforge.py release-test --root . --only "clean release artifacts" --only "doctor-project"
```