# ProcessForge Machine Acceptance Matrix

Run: `pf-machine-acceptance-20260829`
Candidate: local unpublished `1.2.1`
Final installed version: restored `1.1.0`

| Area | Final evidence | Result |
|---|---|---|
| Candidate archive | 894 entries; SHA-256 `9722d7e87b52bec52926cfaa801c49ced588867fd78fd66c62f08acdf36040e1`; version parity in archive/manifest/constants | PASS |
| Extracted release | Full `release-archive-test` from the final archive, 1105.41 s | PASS |
| Updater isolation | Confirm gate, normal apply, local-change blocking, forced rollback, corrupt ZIP rejection, repair classifications | PASS |
| Real installed upgrade | Target-side `core-update`: `1.1.0 -> 1.2.1`, no blockers or local modifications; installed smokes passed | PASS |
| Exact rollback | Target-side `core-update`: `1.2.1 -> 1.1.0`; 868 owned files, missing 0, mismatch 0 | PASS |
| Baseline identity | Manifest SHA-256 `d710b331...15b75`; original ZIP SHA-256 `fd4c9948...f43dc` | PASS |
| Codex hooks | Eight events use one installed PF entrypoint; PF-only automatic trust; foreign handler disables trust | PASS |
| PF-first agent | Fresh installed worker called `pf.context`, `pf.work.start`, `pf.resolve`, `pf.search` before filesystem work | PASS |
| Knowledge routing | PF returned Joomla package/resource IDs and authoritative knowledge/source paths; no narrow plugin article was found | PASS WITH CONDITION |
| Joomla project | `D:/Dev/plg-content-varreplace`; governed run completed 5/5; review and quality gates passed | PASS |
| Joomla runtime | Plugin id 252 enabled on Joomla 6.1.2; HTTPS body contains `PF runtime marker: тест`; `{vAR}` absent | PASS |
| Telemetry and chat | Native hooks, events, raw worker IO, chat transcripts, context telemetry, Agent Ledger check-in/heartbeats/check-out | PASS WITH CONDITIONS |
| Final Runtime | PID 10404; `/readyz` ready; doctor mandatory checks pass; 1.1.0 scheduler tick reproduces known timeout | WARN |
| Final MCP | Hidden `py.exe` PID 10680 with Python child PID 13356, installed 1.1.0 MCP server | PASS |
| Hook preservation | `.codex/hooks.json` SHA-256 unchanged: `0107fce9...bfd9c` | PASS |

## Residual Conditions

- `gpt-5.3-codex-spark` was unavailable because of the machine quota; governed acceptance workers used `gpt-5.5` and recorded that deviation.
- Browser backend was unavailable; Joomla behavior was verified against a real HTTPS frontend response instead of a screenshot.
- The restored `1.1.0` is intentionally unchanged and therefore retains the scheduler/status timeout fixed in candidate `1.2.1`.
- The original baseline shell-worker task is marked failed because its launcher hit `[WinError 2]`; the baseline artifact and later direct machine checks supplied the missing evidence.
