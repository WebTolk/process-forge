# Code quality report: accepted-source candidate v3

Candidate tree40282e709d3e04ef95238fe41b9b23aed543b281. V2 evidence applies to V3
because all executable/test bytes are identical; candidate-v3-delta.json proves it.

Actual Ruff0.17.1 lint and format-check exit0 on tools/python-qa helpers,
tests/python_qa, new project/agent_hooks.py, tests/project_hooks/context_safety.
QA helper configured mypy2.4.0 exit0; hook owner/canonical installer targeted mypy
exit0 with --follow-imports=skip to avoid an unrelated whole-Core analysis.
Exact receipts: checks-unit-v3.json and checks-candidate-v2-quality.json.

Four existing changed files (Main, context parser, initialization, canonical
installer) were compared against accepted base with the same Ruff rules.
Both diagnostics sets have321preexisting findings; comparison of counts by
path/code/message/exact source line finds0introduced. That comparison exits0;
the underlying full legacy Ruff diagnostic runs exit1. No global suppression
or claim of a clean whole Core is made. These large legacy files are not mass
formatted; changed behavior is reviewed and covered by focused tests.

New worker files had explicit import/format corrections. Formatter AST equality
and preserved import bindings/non-import AST were recorded in finish/style-checks.
The test bootstrap uses narrow explained E402 exceptions after source-root setup.
QA subprocess sinks were reviewed with narrow B404/B603 annotations; no shell
is invoked. Initial focused Bandit1.9.4 scan passed on the helper modules.
Whole-Core/dependency security audits were not run or claimed. Documentation
rules use PEP8/257/Google; whole-Core documentation remains a future task.

Independent review ../review-final/report.md:PASS. F1–F4 resolved; no findings.
Ruff check operations override mutating project settings, selected venv executable
is not dereferenced, canonical hook conflicts fail before writes. Shared deployed
QA hash matches frozen source: shared-qa-final-install.json. Native assurance
requires these real reports; unavailable/failing required checks block completion.

Limitations: POSIX venv runtime unverified (Windows symlink test skipped);
legacy style debt and whole-Core typing/coverage remain outside this scope.
Source/archive/installed/actually loaded host evidence remain separate.
