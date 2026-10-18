# Primary implementation acceptance and ownership handoff

2026-09-10, primary orchestrator. Both final implementation attempts exited 0 and worker-run collect returned DONE. Source ownership transfers back to primary. F01 attempt 1 and F02 attempt 1 are preserved and rejected for public test portability workarounds; corrected source retains standard TemporaryDirectory, no Git/HEAD/private scratch coupling.

Accepted behavior: Workplace maintenance stays shared; query uses project authorization at ResourceSearchIndex/SQL boundary. Added unowned target/ancestor conflicts block Core apply before writes and cannot be overridden by force_local_modifications. Changes are bounded to two core files, three registered smokes, and new public fixture helper. No lower-level search or CLI changes.

Primary genuine unmodified test execution (same Python, outside worker sandbox):
- targeted-core-update: PASS, 17.049 seconds. Symlink/broken symlink SKIP WinError 1314; not claimed passed.
- targeted-search-security: PASS, 76.088 seconds.
- targeted-sessionless: PASS, 28.041 seconds.
- targeted-search-narrowing: PASS, 1.362 seconds.

Isolated public copy validation: both corrected updater and security smokes PASS without .git/.pf. Replacing only the two product modules in the isolated copy with pinned baseline 1aecc18b makes the respective new smoke assertions FAIL. See isolated-validation.json and baseline-*.stderr.txt for exact failures; shared source never reverted.

Source-preservation.json: PASS, no changed tracked public file outside declared scope; previous dirty docs and required-output fix preserved by byte hashes.

Worker sandbox tests are limited by TemporaryDirectory WinError 5. Worker F02's private monkeypatch/fixed-temp results are supplemental only; primary's unmodified tests above establish acceptance. F02 attempted alternate D:/tmp scratch during diagnosis, outside the intended owned scratch remit; no product edit relies on it, no such attempt counts as normal test acceptance. Recorded in worker transcript. Do not repeat sandbox diagnosis.

Next: report-only assurance and independent code review, public checksum refresh and full source gates. This accepts implementation for assurance, not release readiness. F03-F12 remain outside this batch.
