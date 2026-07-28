# Installation

ProcessForge is installed as a file-first Python tool. Clone or unpack the
distribution once, then use it to initialize a workplace and onboard projects.

```bash
git clone <processforge-repo> process-forge
cd process-forge
python -m pip install -r requirements.txt

python bin/pf.py version
python bin/pf.py release-test --root .
```

Use `python bin/pf.py` from the ProcessForge distribution root.

After a project is onboarded, use the project runtime launcher inside that
project:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Do not copy the full ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders. The agent configuration only
needs a short instruction that points to the tool installation and tells the
agent to read `.pf/START_AGENT_HERE.md` inside the project.

## Verify The Installation

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-test --root . --trace-smokes
```

`--trace-smokes` writes `.pf/runtime/release-test/latest-trace.ndjson` with the
current smoke name, elapsed time, timeout budget, and timeout reason.

## Requirements

Runtime requirements:

- Python 3.11+ is recommended.
- Python 3.10+ is allowed only when the current tests confirm compatibility.
- Python package dependencies from `requirements.txt`, currently `PyYAML`.
- Use a UTF-8 capable filesystem.
- Read/write access is required for the ProcessForge distribution, workplace, and project folders.
- PowerShell is not required for runtime usage.
- ProcessForge v0.1 does not require a daemon or background process.

## Windows PowerShell UTF-8

PowerShell may render UTF-8 Russian text incorrectly if the console encoding is
not UTF-8. The files remain UTF-8; this is a console rendering issue.

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
```

Identifiers and YAML remain ASCII-safe; docs are UTF-8.

Development and release-check requirements:

- Python 3.11+.
- Python package dependencies from `requirements.txt`.
- Git for source installation and release checks such as `git diff --check`.
- Ability to run subprocesses and create temporary directories.
- ZIP support from the Python standard library.

Git is recommended for installing from source and required for development/release checks. Normal runtime usage from a release archive does not require Git unless the user wants version-control integration.
