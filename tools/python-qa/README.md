# Shared Python quality tools

This bundle installs Ruff, pytest, pytest-cov, coverage.py, mypy, Bandit and
pip-audit once in the workplace tool layer. It stays outside project repositories
and the replaceable ProcessForge Core. These are development dependencies.

Install from the distribution with explicit operator-selected shared directories:

```powershell
python tools/python-qa/install.py --tools-root <shared-tools>/python-qa --toolchains-root <shared-toolchains>
```

The installer pins direct versions, validates dependencies, backs up replaced
managed files and records a private installation receipt. An optional complete
requirements.lock.txt pins the resolved environment. Reuse the installation for
projects using the same Python major/minor version. For another Python version,
install a separate shared bundle with --python and another --tools-root.

Run against any project, including paths containing spaces:

```powershell
python <shared-tools>/python-qa/qa.py --project-root <project> lint -- src
python <shared-tools>/python-qa/qa.py --project-root <project> format -- src
python <shared-tools>/python-qa/qa.py --project-root <project> docstrings -- src
python <shared-tools>/python-qa/qa.py --project-root <project> typecheck -- src
python <shared-tools>/python-qa/qa.py --project-root <project> test -- tests
python <shared-tools>/python-qa/qa.py --project-root <project> test -- --cov=src --cov-branch tests
python <shared-tools>/python-qa/qa.py --project-root <project> security -- src
python <shared-tools>/python-qa/qa.py --project-root <project> audit
python <shared-tools>/python-qa/qa.py --project-root <project> versions
```

`format` checks formatting. `format-fix` rewrites formatting; `fix` applies Ruff's
supported safe lint fixes. Unsafe fixes require an explicit forwarded option.
`lint` and `docstrings` explicitly disable fixes, including project `fix` and
`fix-only` settings; mutating flags require the `fix` operation. A project
`unsafe-fixes` setting alone never enables unsafe fixes through this launcher.

Project Ruff, mypy and Bandit configurations take precedence over shared fallback
files. A pyproject.toml without the relevant tool section does not suppress the
fallback. A shared Ruff fallback selected for an otherwise unconfigured project
is explicit; put the project's intended Ruff configuration at its root when
using a more elaborate hierarchy. Pytest and coverage retain native project
configuration discovery; no global discovery paths or coverage threshold are
forced on unrelated projects.

Tests run in the explicit --python interpreter, a detected project .venv/venv,
or the installation's original base interpreter. The selected executable path
preserves venv symlinks instead of resolving them to the base Python. Trusted
shared QA packages are appended after that interpreter's own dependencies. The Python major/minor and
platform must match: the launcher refuses to import binary packages from another
runtime. It never installs or replaces project dependencies. Mypy uses the
project interpreter for dependency discovery. Dependency audit requires the
project's requirements.txt/pyproject.toml, explicit requirements/path options or
an explicit project interpreter; it never silently audits its own QA environment.

## Configuration and standards

PEP 8 and PEP 257 are the baseline; Google-style docstrings use Args, Returns and
Raises when relevant. Use annotations for types, document meaning and side
effects, and keep simple descriptions concise. Ruff documentation rules are an
explicit `docstrings` operation, not a new mandatory whole-project gate.

Official sources:

- https://docs.astral.sh/ruff/
- https://pytest.org/
- https://pytest-cov.readthedocs.io/en/latest/
- https://coverage.readthedocs.io/
- https://mypy.readthedocs.io/
- https://bandit.readthedocs.io/
- https://github.com/pypa/pip-audit
- https://peps.python.org/pep-0008/
- https://peps.python.org/pep-0257/
