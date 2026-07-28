# Process Directory Layout Split Log

## 2026-07-28 - Codex

- Task: implement root-aware process directory layout split for ProcessForge.
- Scope: process catalog layout, process resolver/list/authoring, release boundary, schemas/docs/tests, dogfooding artifacts.
- Files analyzed: `задания/processforge_process_directory_layout_split_master_prompt.md`, `tools/processforge.py`, `processes/*.yaml`.
- Status: started; confirmed current process catalog is flat and branch is clean.
- Follow-up: classify built-in vs cleanup candidates before moving files.

## 2026-07-28 - Codex

- Task: implement root-aware resolver and pre-release catalog cleanup.
- Files changed: `tools/processforge.py`, `processes/core/*.yaml`, `processes/user/.gitkeep`, `processes/custom/.gitkeep`, `packages/process-forge-knowledge-governance.yaml`, process docs/examples/prompts.
- Status: moved confirmed built-in processes to `processes/core/`; kept `user/custom` empty for private/local process definitions; removed `process-template-install` from the public catalog as a pre-release cleanup candidate.
- Verification: `python -m py_compile tools/processforge.py bin/pf.py`, `process-layout-doctor`, and `builtin-process-catalog-doctor --public` passed.
- Follow-up: add deterministic smokes and refresh checksums/release evidence.

## 2026-07-28 - Codex

- Task: add root-aware process layout smokes.
- Files changed: `tools/smoke_process_directory_layout.py`, `tools/smoke_process_resolver_multiple_roots.py`, `tools/smoke_process_list_origin_filters.py`, `tools/smoke_process_authoring_writes_user_root.py`, `tools/smoke_legacy_flat_process_layout_warning.py`, `tools/smoke_release_pack_excludes_user_processes.py`, `tools/smoke_process_id_stable_after_move.py`, `tools/smoke_process_root_collision_policy.py`, `tools/processforge.py`.
- Status: new smokes added to `release-test` command list.
- Verification: all eight new targeted smokes passed.
- Follow-up: run existing process and release validation gates.

## 2026-07-28 - Codex

- Task: complete release validation for process directory layout split.
- Files changed: `.pf/artifacts/process-directory-layout-split-report.md`, `.pf/reviews/process-directory-layout-split-review.md`, `.pf/handoffs/process-directory-layout-split-handoff.md`, `checksums/processforge.sha256`, `dist/processforge.zip`, `dist/processforge.manifest.json`.
- Status: complete; dogfooding artifacts marked ready/pass.
- Verification: `release-test --public --fail-fast --timeout-scale 1`, `release-test --public --timeout-scale 1`, `release-pack`, `release-archive-test --extracted-test full --timeout-scale 1`, checksum check, public cleanliness, process-layout-doctor, and `git diff --check` passed.
- Follow-up: package-installed process roots are still an extension point; this slice reserves the contract but does not implement a full package process registry.
