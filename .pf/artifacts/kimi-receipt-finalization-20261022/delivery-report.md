# Corrective dev delivery

2026-10-22. PASS for the authorized local dev/device profile. Installed final source e4420e6a3b27480bcf0199a7a4ce4acc3eb1da1a, version 1.3.0-alpha1. Archive SHA256 09f0133d7ea81bbc04f155d4746d2cf6acae1a8fe216a0e3ea6a9dc97a81e7ed; native update core-update-20261022T053739Z. This is a distinct correction of the client receipt diagnosis, not a replay of the earlier update.

Native clean-source pack/checksums and quick extracted archive profile pass. Final source and clean-candidate pytest: 92 tests, 13 subtests; Ruff lint/format and mypy pass. Installed verification: 1462/1462 managed files, 2/2 exact backup preimages, prior manifest model preserved, 22 Workplace configuration files and 74 unowned Core files preserved; doctor-workplace 197 PASS, incomplete_update=false, repair=nothing_to_repair.

Only client _delivery_result and checksum differ from the first installed candidate. Entire module AST excluding that client function is identical; no server stop/start/restart or extra guard bypass occurred. Existing restarted PF App Server remains ready with its same PID.

Live synthetic qualification: 9 delivered/accepted HTTP receipts, 8 distinct raw receipts, 5 normalized events and 3 private chat messages. Separate tool calls remain distinct; replay has the same effects; native prompt arrays/subagent identity, failed-tool status and session checkout are verified. See kimi-live-verification.json. Temporary verifier schema mistakes (native envelope payload versus persisted event data) were corrected by read-only verification of already stored receipts; no installation or event sequence was replayed for those mistakes.

Exact source is read back from both dev remotes; GitVerse uses existing token-backed helper. Final safe handoff records follow in a metadata commit. This is neither a real K2.7/K3 model run nor reloaded connected MCP acceptance nor a full public stable release. User can now run Kimi again. Handoff: capture the lessons and close this bounded corrective Work.
