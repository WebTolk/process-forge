# Python code quality

All Python checks use the existing registered PF Python QA launcher. Tools were
already available; no environment installation or host repair was performed.

| Gate | Scope | Result |
| --- | --- | --- |
| Ruff lint | monitor owner and new uptime test | PASS, exit 0 |
| Ruff format check | monitor owner and new uptime test | PASS, exit 0 |
| Mypy | exact source bodies of `collect_snapshot`, `render_details`, `format_uptime`, `render`, with actual source dependencies | PASS, exit 0 |
| New docstring check | exact `format_uptime` source with its used imports | PASS, exit 0 |
| Whole-owner mypy comparison | actual monitor versus original owner, identical import environment | 9 existing diagnostics on each; zero introduced errors |
| Candidate source Git whitespace | all five changed product/distribution paths | PASS, exit 0 |
| Existing behavior AST parity | accepted preimage versus candidate, allowing the intended uptime expression and three equivalent local helper conversions | PASS |

Versions: Python 3.14.3, Ruff 0.17.1, mypy 2.4.0, pytest 9.1.1,
pytest-cov 7.1.0, coverage 7.16.2. Dependency/security tools are unchanged and
were not added as unrelated gates because this slice changes no dependencies.

Reproduction through `<shared-python-qa>/qa.py --project-root <candidate>`:

```text
lint -- tools/pf_runtime/monitor.py tests/runtime_monitor/test_uptime.py
format -- tools/pf_runtime/monitor.py tests/runtime_monitor/test_uptime.py
typecheck -- --follow-imports=silent <task-private>/typed_area.py
docstrings -- <task-private>/docstring_area.py
```

The diagnostic typed area contains the four exact changed function bodies,
imports the actual unchanged module dependencies, and uses the candidate's
`src` and `tools` import roots. Relative `service` import syntax is qualified
only for standalone checking. No error codes are suppressed. Function names,
line locations, and extracted-source hashes are recorded in the sealed manifest.

The owner-wide comparison uses that same import environment for the candidate
and original monitor preimage. Remaining diagnostics concern the unchanged
socket/probe addition, terminal size inference, Windows/POSIX terminal stubs,
character input union, and existing Runtime override metrics union. They are
retained as existing typing debt, not reported as a successful owner-wide gate.
Initial diagnostic attempts and their corrected reruns remain task-private;
correction of diagnostic imports did not change product source bytes.

PF Ruff's baseline found import ordering and three existing assigned lambdas.
Explicit import fixing, conversion of those local helpers to equivalent
functions, and formatting are limited to the monitor owner and new test.
Formatting does not represent continuation of the deferred OOP refactor.
An additional import comparison confirms that every previous module import is
preserved; the only additions are standard-library `calendar.monthrange` and
`datetime.timedelta`.
