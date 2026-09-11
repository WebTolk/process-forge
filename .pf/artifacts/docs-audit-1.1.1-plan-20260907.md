# Documentation/code parity audit for 1.1.1

Status: planned
Run: garage-audit-pf-documentation-against-the-current-codebase-for-1-1-1-pre
Assignment: audit-pf-documentation-against-the-current-codebase-for-1-1-1-prerelease
Owner: primary agent; pinned task-batch-execution disallows delegation.
Baseline: dev at 1aecc18b6824204ca45ab30241b92d26e6d583a5 plus the preserved uncommitted required-output fix. VERSION currently 1.1.0; 1.1.1 is the requested target, not a published version claim.

## Scope and method

1. Inventory public documentation: README/QUICKSTART EN/RU, docs, prompts, Markdown templates and release guidance. Identify current vs historical/draft statements.
2. Extract documented CLI invocations and compare their command/options to the current argparse tree without dispatching commands. Check local Markdown links. Record coverage and exclusions; manually adjudicate automated findings.
3. Trace key behavior against code/schemas: initialization and roots, Garage/Forge and Ledger, declarative process stages/evidence, allowed processes, search/index model, resource discovery, hooks, task outputs, Core updates and workplace migrations.
4. Audit release/version documentation and entrypoint discoverability, including EN/RU parity. Current source is authoritative; historical release notes need not claim 1.1.1 prematurely.
5. Run targeted documentation/contract checks only. Reuse the immediately preceding full-suite result as explicitly prior-turn evidence; do not call that full result a fresh audit run.
6. Produce prioritized findings with exact doc/code locations, impact, recommended changes and prerelease acceptance gates; review evidence and close the governed audit.

Allowed writes: this audit's .pf artifacts, logs, review, handoff, generated PF state and a private reproducible audit helper. No product code/documentation edits, version changes, packaging, publishing, installed Core or external project changes.

Current result: pending. Expected artifacts: inventory/evidence, audit findings, remediation plan, validation result and final handoff.
