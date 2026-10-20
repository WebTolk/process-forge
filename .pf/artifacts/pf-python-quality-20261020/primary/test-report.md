# Test report: accepted-source candidate v3

Candidate tree40282e709d3e04ef95238fe41b9b23aed543b281, base84d0f2c681dbcf861128d5098c8db2c938c3e918.
V3 has37 identical files from V2 and one native project tool-overrides file;
executable/test bytes are identical (candidate-v3-delta.json).

Actual command: shared QA launcher with explicit project/tool roots,
`test -- -q tests/python_qa tests/context_safety tests/project_hooks`.
Exit0:73passed,1skipped,38subtests passed; checks-candidate-v2.json records hashes.
The skip is Windows permission to create an interpreter symlink; real POSIX
execution is not qualified. Unit tests still cover interpreter selection/ABI,
argv/config/exit handling; two independent project fixtures exercise a real
project venv, project-only dependency and negative test/lint/type outcomes.

Context15 regressions cover no implicit writes, JSON, missing/broken/stale
snapshots, live byte changes and explicit write workflows. Hook31 tests include
Forge/Garage, idempotence/custom settings, failures/unsafe paths/revision changes,
all8events/later PF handler, wrong type/duplicates/manual status, full CLI/MCP
initialization and local ingress binding/provenance/deduplication. QA28 cases
include project configs/interpreter/ABI, install isolation and explicit fix modes.

Real Ruff fixture regression: old V1 changed files under project fix/fix-only/
unsafe settings; current checks preserve bytes and unsafe fix requires an
explicit flag. All expected exit codes match: ruff-mode-regressions.json.
Earlier four affected initialization smokes and current canonical installer
smoke pass. Native process contract, official discovery and minimal Run smoke
pass; native override doctor plus8activated IDs/fresh readiness pass.

Versions: Python3.14.3, pytest9.1.1, pytest-cov7.1.0, coverage7.16.2; QA module
coverage77%, not a whole-Core metric. Source evidence was independently reviewed:
../review-final/report.md PASS, no findings, all38source/payload hashes match.
Browser/UI tests are not applicable: this scope changes CLI/Core/config/tooling,
no browser behavior. Archive/installed/connected proof is tracked separately.
