# Installation

ProcessForge is installed as a file-first Python tool. Clone or unpack the
distribution once, then use it to initialize a workplace and onboard projects.

```bash
git clone <processforge-repo> process-forge
cd process-forge

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
```

## Requirements

Runtime requirements:

- Python 3.11+ is recommended.
- Python 3.10+ is allowed only when the current tests confirm compatibility.
- Use a UTF-8 capable filesystem.
- Read/write access is required for the ProcessForge distribution, workplace, and project folders.
- PowerShell is not required for runtime usage.
- ProcessForge v0.1 does not require a daemon or background process.

Development and release-check requirements:

- Python 3.11+.
- Git for source installation and release checks such as `git diff --check`.
- Ability to run subprocesses and create temporary directories.
- ZIP support from the Python standard library.

Git is recommended for installing from source and required for development/release checks. Normal runtime usage from a release archive does not require Git unless the user wants version-control integration.
