# Beta Baseline Audit

Task: `beta-baseline-audit-20260822`
Run: `beta-release-qualification-20260822`
Status: baseline identified; use clean clone for qualification.

## Candidate Commit

Current checkout and local `origin/dev` both resolve to:

`654cd405c121dcdb242438cf31052ecd7c7c88b0`

Short commit: `654cd40`
Subject: `fix: make release checksum checkouts deterministic`
Commit date: `2026-08-21T22:16:50+04:00`
Author: `sergeytolkachyov`

Local divergence check:

- `HEAD...origin/dev`: `0 0`
- `origin/dev..HEAD`: no commits
- `HEAD..origin/dev`: no commits
- Branch: `dev`
- Tracking: `origin/dev`
- Remote: `https://github.com/WebTolk/process-forge.git`

Scope note: no network fetch was performed in this read-only worker context, so this verifies the local tracking ref, not the live remote server state.

## Checkout State

Tracked tree is clean:

- no unstaged tracked diff
- no staged diff
- no ahead/behind against local `origin/dev`

The checkout is not operationally clean because it contains untracked local process artifacts.

## Local Artifacts To Preserve

There are 21 untracked files that should be preserved before any cleanup, reset, or clone replacement:

- `.pf/artifacts/beta-release-qualification-20260822/orchestrator-plan.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/final-validation.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/independent-architecture-review.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/independent-code-review.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/mcp-search-implementation-report.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/mcp-search-proof.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-implementation-report.md`
- `.pf/artifacts/project-init-local-search-mcp-20260821/project-initialization-proof.md`
- `.pf/assignments/beta-baseline-audit-20260822.yaml`
- `.pf/assignments/beta-installation-contract-audit-20260822.yaml`
- `.pf/assignments/beta-mcp-security-matrix-20260822.yaml`
- `.pf/contexts/assignment-capsules/beta-baseline-audit-20260822.capsule.yaml`
- `.pf/contexts/assignment-capsules/beta-installation-contract-audit-20260822.capsule.yaml`
- `.pf/contexts/assignment-capsules/beta-mcp-security-matrix-20260822.capsule.yaml`
- `.pf/runs/beta-release-qualification-20260822/plan.md`
- `.pf/runs/beta-release-qualification-20260822/run.yaml`
- `.pf/runs/beta-release-qualification-20260822/task-index.md`
- `.pf/runs/beta-release-qualification-20260822/worker-prompts/beta-baseline-audit-20260822.md`
- `.pf/runs/beta-release-qualification-20260822/worker-prompts/beta-installation-contract-audit-20260822.md`
- `.pf/runs/beta-release-qualification-20260822/worker-prompts/beta-mcp-security-matrix-20260822.md`
- `logs/project-init-local-search-mcp-commit-push-report-20260821.md`

## Clean Clone Requirements

Beta packaging and qualification should not use the active checkout.

Use a fresh clone from `https://github.com/WebTolk/process-forge.git`, checkout `dev`, and verify:

- fetched `origin/dev` is the intended candidate commit;
- `HEAD` equals `654cd405c121dcdb242438cf31052ecd7c7c88b0` or a newer explicitly selected fetched `origin/dev`;
- `git status --short --branch` is clean before archive build;
- no untracked `.pf` run, assignment, capsule, review, runtime, or log artifacts are present in the packaging tree;
- generated archive evidence records commit SHA, archive SHA-256, file count, manifest/checksum validation, and install paths.

## Qualification Gate Impact

GO/NO-GO qualification can proceed from a clean clone at the candidate commit.

The active checkout should remain evidence-preserving only. It is suitable for orchestration/report custody, not for deterministic beta archive production.
