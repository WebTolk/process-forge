## 2026-08-14 19:16 - orchestrator

Task:
Build and manually activate ProcessForge 1.1.0-dev from the current dev work.

Files changed:
- Workplace distribution registry now selects the versioned 1.1.0-dev distribution.
- Project context snapshot and update-assessment evidence were refreshed.

Artifacts changed:
- Manual package-update run, worker reports, summary, and handoff under `.pf/`.

Tools used:
- ProcessForge shell workers: gpt-5.3-codex-spark for version/package input audit; gpt-5.4 for release-surface audit.
- Release pack, release-archive test, workplace doctor, project upgrade/context checks.

Decisions:
- Use a side-by-side `1.1.0-dev` distribution, not an overlay of 1.0.2.
- Keep the prior distribution and a registry backup as the rollback path.
- Include `src` in the temporary package build because extracted-archive execution proved it is required by the new Core import seam.

Risks:
- The archive's quick release test still reports the pre-existing public-cleanliness baseline findings for `scratch` and a Windows-path test pattern; this build is therefore dev-only, not an RC.
- The temporary build-only packaging correction is not a new commit on `dev`.

Next steps:
- Use the selected distribution for normal workplace commands. Before promoting to RC, commit the release-surface correction to the source branch and clear the public-cleanliness baseline failures.

Handoff:
- Previous distribution remains available for registry rollback.
