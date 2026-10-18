# T06 change record

Status: ready_for_review. No production service code changed.

Added tools/smoke_prepared_execution_recovery.py and registered it in release_test_commands with a 240-second timeout. The test promotes actual subprocess death/dead-owner recovery, governed offline execution/collection invariance, separate source MCP reconnect/transition and actual directory redirect refusal from T05 evidence to standard QA. It creates scope before immutable fixture context, checks exactly-once events and removes only the verified temporary Junction/link.

Updated EN/RU runtime-drivers.md, runtime-mcp.md, declarative-process-execution.md, and EN garage-core.md (there is no existing RU garage-core.md). Corrected prepared versus legacy Codex input, worker output declarations, reserved input pointers, scope versus OS sandbox, new MCP Work read routes, identity checks after reconnect and evidence-layer distinctions. Existing T01-T05 docs remain authoritative and frozen proof files are untouched.

Focused developer check: python -B tools/smoke_prepared_execution_recovery.py exited 0 with three PASS lines: offline governed execution/collection/reconnect/transition; actual process death/dead-owner exactly-once recovery; real directory redirect refusal without private publication. This is deterministic source fixture evidence, not updated installed-host proof.

Remaining implementation-derived update: regenerate checksums after final assurance fixes. Baseline hashes for 561 frozen files and nine planned existing files were recorded before product edits. Broad suite and semantic review follow in code-assurance.
