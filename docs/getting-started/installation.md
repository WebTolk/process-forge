# Installation

Install ProcessForge once as a Python tool, then create a workplace and onboard
projects. Start with [requirements](../requirements.md), including SQLite,
certificate trust, permissions and memory planning.

## Get the distribution

Extract an official release archive to a dedicated directory, or clone the
repository when installing from source:

```bash
git clone <processforge-repo> process-forge
cd process-forge
```

An archive installation does not require Git. Keep mutable workplaces, projects
and the Python environment outside the replaceable distribution. These examples
use sibling directories `../pf-venv`, `../pf-workplace` and `../my-project`.

## Create an isolated Python environment

On Linux/macOS, from the distribution root:

```bash
python3 -m venv ../pf-venv
source ../pf-venv/bin/activate
python -m pip install -r requirements.txt
python bin/pf.py version
```

On Windows PowerShell:

```powershell
py -3 -m venv ../pf-venv
../pf-venv/Scripts/python.exe -m pip install -r requirements.txt
../pf-venv/Scripts/python.exe bin/pf.py version
```

Choose the intended installed Python before creating the environment. If `venv`
or `pip` is missing, provision it using your OS's Python installation instructions.
Use `python -m pip` from that environment so PyYAML is installed for the same
interpreter that runs PF.

In the remaining examples, `python` means this environment's interpreter. On
Windows you can invoke `../pf-venv/Scripts/python.exe` directly without activating
PowerShell scripts or changing execution policy. After changing directory,
adjust that path or use its full path. An optional Runtime/MCP registration
must also use an interpreter with these dependencies; `--python` can pin it.

## Check before creating state

Run the [read-only preflight](../requirements.md#read-only-preflight), then:

```bash
python bin/pf.py version
python bin/pf.py --help
```

These checks do not install services or create a workplace. For a human-led
first setup, continue with [Guided workplace setup](guided-workplace-setup.md).
The agent collects answers and uses existing file-based setup commands.

For automatic software-development setup with known paths and resources,
preview the workplace, inspect the plan, then apply:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --dry-run
python bin/pf.py workplace-init --workplace ../pf-workplace --profile software-development --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Prepare required shared resources before onboarding. Preview against an existing
project directory; apply can also create a new project root:

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

`first-run` is a shortcut and does not accept `--profile`; use the two-command
flow above to select a bundled workplace profile. See [First run](first-run.md)
and [Initialization order](initialization-order.md).

## Use the linked project

After onboarding, run the project-local launcher inside the project:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py project-context-check --project-root .
```

Use `python bin/pf.py` from the distribution root, not from a normal project.
Do not copy the full repository into `.codex`, `.claude`, `.agents`, or similar
agent configuration folders. Project entry uses root `AGENTS.md`, with an
explicit `.pf/AGENTS.md` fallback in an unmigrated project. Select the loader or
adapter described in [agent entry](../concepts/agent-entry.md).

Garage does not require PF Runtime, MCP or Codex hooks. Connect them only when
the operator chooses the relevant workflow; ordinary project work does not
install, start, restart or repair infrastructure. See
[Runtime and MCP startup](runtime-autostart.md).

## Development and release verification

These are broader checks for a source checkout or staged release, rather than
read-only preflight. They need subprocesses and writable report/scratch locations;
development/release checks may also need Git:

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-test --root . --trace-smokes
```

`--trace-smokes` writes `.pf/runtime/release-test/latest-trace.ndjson` with the
current smoke name, elapsed time, timeout budget, and timeout reason. A modified
checkout can differ from the published checksum inventory; checksum validation
is not a substitute for context or capsule validation.

## Windows PowerShell UTF-8

If Russian text displays incorrectly, set the console encoding. The files
remain UTF-8:

```powershell
chcp 65001
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
```

Identifiers and YAML remain ASCII-safe; documentation uses UTF-8.
