# T05 prepared execution context regression handoff

Role: focused regression writer. Date: 2026-09-26.

Owned files: `tools/smoke_prepared_execution_context.py` and this report.

Validation: `python -B tools/smoke_prepared_execution_context.py` completed and printed `PASS: prepared-input schema/budgets, empty and denied grants, semantic driver/model invariance, source/intent/manifest drift denial, offline generic-shell same-attempt launch, receipt interruption repair/idempotent collection/output attribution, metadata/fulltext drift and revocation, explicit empty stage subset`. The smoke validates generated manifests against `schemas/prepared-input.schema.json`, exercises exact 64 KiB inline-file and 256 KiB aggregate budgets, enforces the 4 MiB manifest ceiling, and runs an offline generic-shell executor with sockets disabled and no MCP environment. It checks same-attempt explicit prepare/start, immutable tampered old manifest, explicit reprepare for blocked state, stable semantic fingerprints across driver/model changes, denied source/intent/resource changes, metadata-only body exclusion, fulltext drift and revocation, output attribution, report size/UTF-8 preflight, and receipt retry/idempotence. A `prompt_payload` regression proves prepared Codex input ignores worker prompt/capsule/workspace files after a manifest is supplied.

Collection coverage uses the fixture's legacy run/task path, so it expects the compatibility completion events. The primary agent owns a separate genuine governed collection preservation regression; this smoke does not claim governed lifecycle preservation. Actual connected-host acceptance and installed-process acceptance remain outside this source-level fixture.

Implementation findings passed to the primary: the prepared-input schema initially expected bare 64-hex resource digests while T02 emits `sha256:`-prefixed digests. The schema owner corrected the field to the shared digest definition; the focused smoke then passed. No product changes were made in this responsibility.

Residual boundary: temporary isolated project/workplace only; no network, MCP server, installed process, or external host was exercised.
