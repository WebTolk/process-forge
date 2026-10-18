# investigation

Status: ready; primary / release-engineer, 2026-10-17.

Investigated native release-pack, release-archive-test full and timeout semantics, config read and core-update status/plan/apply contracts. Native installed status: 1.2.0, 1307 managed files, incomplete_update=false. App-server observed ready, scheduler_alive=true, active_workers=0, pending_runtime_jobs=0. Its process and source provenance are private checkpoint evidence. server stop uses expected_instance_id and require_idle, unlike ordinary runtime alias; use guarded server commands. Existing baseline reports distinguish source, archive, installed, Runtime and actual connected MCP. Current source is a new executable candidate and requires complete qualification. Native source checksum passed in clean LF detached worktree. Source pushes failed DNS and remain pending. Impact: public API schemas unchanged; installed mutable/private config/history must survive.

Next: follow the pinned native process and ../plan.md; do not edit this evidence after transition.
