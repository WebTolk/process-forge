# Shared Python quality tools

The portable bundle in [tools/python-qa](../../tools/python-qa/README.md) installs
development tools once in the workplace tool layer, outside projects and the
replaceable PF Core. Register its launcher in the workplace tools registry so
different projects can resolve the same installation.

It includes Ruff, pytest, pytest-cov, coverage.py, mypy, Bandit and pip-audit.
Use the shared Python toolchain contract for tool categories and configuration
precedence. Project configuration and application dependencies take precedence;
the shared defaults apply only when the corresponding local configuration is
absent. No project is automatically reformatted or subjected to a full scan.

```powershell
python <shared-tools>/python-qa/qa.py --project-root <project> lint -- src
python <shared-tools>/python-qa/qa.py --project-root <project> format -- src
python <shared-tools>/python-qa/qa.py --project-root <project> typecheck -- src
python <shared-tools>/python-qa/qa.py --project-root <project> test -- tests
```

`format` checks. `format-fix` writes formatting; `fix` applies supported lint
fixes. `lint` and `docstrings` disable project `fix`/`fix-only` settings; unsafe
fixes require an explicit `fix -- --unsafe-fixes` operation. Documentation checks
use the explicit `docstrings` operation. Arguments
after `--` are passed unchanged to the selected tool. Exit statuses, including
failed tests and type errors, remain failures.

Tests run in the actual selected project interpreter with shared QA packages
appended after its dependencies. Python major/minor version and platform must
match the QA environment. Install another shared bundle for a different Python
version; never substitute another interpreter silently. The launcher does not
install application dependencies. Dependency audit selects project manifests
or an explicitly selected environment, rather than the QA environment itself.

Use PEP 8/257 and the Google docstring convention for new documented Core areas.
Describe responsibilities, useful arguments/results, exceptions, constraints and
side effects where relevant. Keep types in annotations. The separate Core
documentation and systematic unit-coverage tasks remain future work; tests added
for this delivery do not establish whole-Core coverage.

See the bundle README for installation, interpreter overrides, tool sources and
the complete command list. This setup changes neither PF process stages nor
project permissions, and adds no development dependency to PF Runtime.
