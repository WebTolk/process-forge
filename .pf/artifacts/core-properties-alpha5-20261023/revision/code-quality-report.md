# Registered Python quality for af68fecf

The corrected full task is31 files; candidate manifest/commit bind every byte.
Registered shared launcher uses the actual Python3.14.3 environment, Ruff0.17.1,
mypy2.4.0, pytest9.1.1, coverage7.16.2 and Bandit1.9.4. No QA/runtime dependency
was installed. Tool contract and six Python source hashes are retained in the
primary's pinned Python inputs; current successor MCP resolve provenance is in
python-provenance.json. New source uses frozen dataclasses, a narrow structural
reader Protocol, explicit composition, typed JSON shapes and fresh containers.

Commands use the PF-registered python-qa launcher with the explicit isolated
checkout. Actual command/output/exit receipts are retained in revision scratch.

| Gate | Result |
| --- | --- |
| Ruff lint new owner and all5 Core test files, no cache | exit0, no findings; correction-lint-final |
| Ruff format owner, changed tests and adapter hunks | exit0,24 scoped checks; format.json |
| Ruff format all5 Core tests | exit0; correction-test-format-final |
| Strict mypy owner, follow-imports=skip, ignore-missing-imports | exit0,1 file; correction-strict-owner-final |
| Mypy changed action dependency/adapter seam, same import boundary | exit0; correction-action-types-r2 |
| Mypy4 affected Runtime modules | exit1,53 legacy diagnostics, identical exact-baseline multiset; runtime-type-delta.json, introduced0 |
| Full affected-file Ruff differential | baseline383, candidate381, introduced0; lint-delta.json |
| Owner Google docstrings | exit0; correction-owner-docstrings |
| Owner Bandit | exit0,308 LOC, no issues; correction-owner-security |
| Owner branch coverage |97% combined,181 statements/3 missing,56 branches/4 partial; correction-properties-coverage |

Earlier four typed Core composition/bootstrap/release modules retain their
exact b2dc2ec0 bytes and passing primary-check-types receipt. Factory/import/
concurrent-first-call cases remain in the permanent suite. Earlier formatting
changes preserve whole-file ASTs; correction format-fix also retained complete
AST equality in its scoped receipts. Fixture relocation is intentional code,
covered by fresh pytest and clean Ruff, not mislabeled AST-only formatting.

Initial correction test4 failures, first fixture-import lint failure and first
action mypy no-redef failure remain retained. Fixes: one captured owner in MCP
composition, complete healthy doctor fixture, shared fixture owner in conftest,
and an unambiguous discovery result variable. Successful reruns replace the
failed conclusions without deleting or rewriting failure receipts.

The old monolith is not globally lint/type clean. Differential checks do not
waive new findings: none were introduced. No pip-audit is applicable because
dependencies did not change. Source native/archive/device/actual connected-host
qualification remains separate from this scoped code-quality result.
