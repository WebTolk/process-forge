# Set up a contributor agent on a new device

[Русская инструкция](../ru/contributors/agent-setup.md)

Follow this guide after cloning ProcessForge when the requested workstation setup
includes shared PF knowledge and agent tools. Read [AGENTS.md](../../AGENTS.md)
and [CONTRIBUTING.md](../../CONTRIBUTING.md) first. Initial reading and setup are
possible before PF Work exists. Substantive development then uses your own local
PF context and Work. This setup creates a separate workplace and local ignored
project state, without reconstructing another developer's `.pf` history.

## 1. Source, access and directories

Use Git, GitHub CLI (`gh`), Python 3.11+ with pip/venv, and a UTF-8 shell. Install
missing executables from their official distributions or the device's package
manager. Reuse available credentials; use `gh auth login` only when authentication
is missing. GitVerse access is needed for the post-merge mirror. Store credentials
in the credential manager, never in URLs, this profile or an agent prompt.

```sh
git clone --branch dev https://github.com/WebTolk/process-forge.git
cd process-forge
git status --short --branch
git remote -v
git fetch origin
git switch -c work/agent-bootstrap origin/dev
gh auth status
```

For an existing clone, inspect and preserve its state before switching branches.
Configure Git author identity if it is absent. Add the canonical GitVerse remote
only if missing, as described in CONTRIBUTING. Record `git rev-parse HEAD`.

Choose these **absolute local paths** once; names below are variables, not fixed
drive letters or a requirement for a global `.agents` directory:

| Name | Purpose |
| --- | --- |
| `Repo` | Working source checkout. |
| `Core` | Separate PF installation pinned to a known release or source revision. |
| `PfPython` | Interpreter of the PF installation's external virtual environment. |
| `DevPython` | Interpreter of the source development environment, also outside the checkout. |
| `Workplace` | Mutable PF workplace, separate from both source and Core. |
| `Tools`, `Toolchains` | Shared executables/environments and toolchain contracts. |

On PowerShell use `& $PfPython ...` to invoke a path; on POSIX use
`"$PfPython" ...`. Replace paths explicitly, including when they contain spaces.
Do not overwrite an existing installation to repeat first-time setup.

## 2. Python and PF

For this contributor workflow, use a separate Core checkout of the recorded
`origin/dev` revision, or a release explicitly verified for the same capabilities.
The published knowledge bootstrap was verified with source `d0d18f7d`; old Core
1.2.0 rejects an external JSON Schema reference during package doctor and is not
a qualified Core for this setup. Instructions on `main` still direct development
to a working branch from `dev`; they do not upgrade the stable runtime.
A source-pinned installation can be prepared
with `git clone --no-hardlinks <Repo> <Core>`, followed by
`git -C <Core> checkout --detach <recorded-revision>`. Its mutable workplace and
Python environment stay outside Core. This is distinct from the working branch.

Create two environments using the chosen Python executable:

```sh
python -m venv <pf-environment>
python -m venv <development-environment>
<PfPython> -m pip install -r <Core>/requirements.txt
<DevPython> -m pip install -r <Repo>/requirements.txt
<DevPython> -m pip install types-PyYAML
<PfPython> <Core>/bin/pf.py version
```

On Windows the executable is `Scripts/python.exe`; on POSIX it is `bin/python`.
`types-PyYAML` supports development type checking; it is not a Runtime dependency.
The checked-in requirements are authoritative: install **both PyYAML and
jsonschema**, rather than copying an older dependency list.

Check the selected PF interpreter's standard-library capabilities:

```sh
<PfPython> -c "import sqlite3, ssl, zlib, venv, yaml, jsonschema; d=sqlite3.connect(':memory:'); d.execute('create virtual table t using fts5(text)'); print(sqlite3.sqlite_version, ssl.OPENSSL_VERSION); d.close()"
```

Follow the additional [requirements checks](../requirements.md), including
Windows `ctypes` and storage permissions. For a new workplace:

```sh
<PfPython> <Core>/bin/pf.py workplace-init --workplace <Workplace> --profile software-development --dry-run
<PfPython> <Core>/bin/pf.py workplace-init --workplace <Workplace> --profile software-development --apply
<PfPython> <Core>/bin/pf.py doctor-workplace --root <Workplace>
```

`software-development` selects the bundled development processes. Select the
process appropriate to the task; it complements the contribution/delivery rules.
The profile does not supply the Python knowledge packages below. Inspect an
existing workplace before enabling a pack; do not rerun `workplace-init` to update it.

## 3. Shared knowledge packages

The reviewed initial versions and ZIP hashes are in
[knowledge-packages.json](knowledge-packages.json). This file is an input to the
contributor installer and agent instructions, not a substitute for a native PF
project context. The standard setup installs all five packages; read their
document indexes first and load content only when relevant.

| PF package | Canonical repository | Use |
| --- | --- | --- |
| `docs.python` | [pf-python-knowledge](https://github.com/WebTolk/pf-python-knowledge) | Language and standard library: pathlib, subprocess, asyncio, typing and related references. |
| `docs.python-practices` | [pf-python-practices-knowledge](https://github.com/WebTolk/pf-python-practices-knowledge) | HOWTOs, design practices, annotations and typing guidance. |
| `docs.python-peps` | [pf-python-peps-knowledge](https://github.com/WebTolk/pf-python-peps-knowledge) | PEP 8/257, typing, packaging and language proposals. Check each PEP's status and target Python version. |
| `docs.python-packaging` | [pf-python-packaging-knowledge](https://github.com/WebTolk/pf-python-packaging-knowledge) | Environments, pyproject metadata, distribution and dependency work. |
| `docs.python-devguide` | [pf-python-devguide-knowledge](https://github.com/WebTolk/pf-python-devguide-knowledge) | CPython contribution/reference practices, when applicable. PF's own CONTRIBUTING remains authoritative. |

Each initial public version is `1.0.1`; resource id is `root`. These are selected
2026-10-02 snapshots, not complete or continuously refreshed upstream mirrors.
Some pages describe a newer Python than the minimum supported interpreter.
`sources.json`, document front matter and `NOTICE.md` preserve provenance and
per-document licensing. PF-specific architecture and contracts remain in this
repository's versioned `docs/` and nested `AGENTS.md` files.

From the source checkout, using its development environment:

```sh
<DevPython> <Repo>/tools/install-contributor-knowledge.py --workplace <Workplace>
<DevPython> <Repo>/tools/install-contributor-knowledge.py --workplace <Workplace> --apply
```

The helper supports the standard `global` package root `<Workplace>/packages`.
It downloads version-specific ZIPs, verifies the pinned SHA-256 and package
identity, rejects unsafe archive paths, and records exact dotted installation
paths in `registries/installed-subjects.yaml`. It preserves unrelated records.
An already installed matching snapshot is checked and retained; another version
or modified content requires the native updater, not an overwrite. For an offline
setup, download the five named ZIPs beforehand and pass `--archives-dir <directory>`;
the same hashes are still required. Custom package roots require an explicit
installation and matching installed-subject path rather than this helper.

For every id from the profile, run:

```sh
<PfPython> <Core>/bin/pf.py knowledge-package-doctor --workplace <Workplace> --package <id> --package-root global
```

The delivered resource indexes are already present. If package metadata is
intentionally changed, use `knowledge-index-refresh --workplace <Workplace>
--package <id> --package-root global --apply` and check the package again.

For **ProcessForge source development**, select these packages in your local
project context requirements using their stable ids/resource `root`, then refresh
and check the project context. Read resource indexes first and only relevant pages.
Native PF search and Work resource access use that project's valid snapshot and
authorized selections; installing a workplace package alone does not select it.

## 4. Python quality tools

Install the shipped bundle outside the source and Core directories using the
same Python major/minor as the development environment:

```sh
<DevPython> <Repo>/tools/python-qa/install.py --tools-root <Tools>/python-qa --toolchains-root <Toolchains>
<DevPython> <Tools>/python-qa/qa.py --project-root <Repo> --python <DevPython> versions
```

This supplies **Ruff, pytest, pytest-cov, coverage.py, mypy, Bandit and pip-audit**,
their pinned direct versions, launcher and Python toolchain contract. Read
[the bundle guide](../../tools/python-qa/README.md). Project configuration takes
precedence. Use a separate bundle for another Python minor version or OS.

Register the actual launchers in PF with `tool-register --workplace <Workplace>
--id <id> --name <name> --capability <capability> --command <quoted-command>
--healthcheck <quoted-healthcheck> --apply`:

| Tool id | Capability | `qa.py` operation |
| --- | --- | --- |
| `python-ruff` | `lint` | `lint` |
| `python-formatter` | `format` | `format` (checks; `format-fix` writes) |
| `python-pytest` | `test_running` | `test` |
| `python-coverage` | `coverage` | `test -- --cov=src --cov-branch tests` |
| `python-mypy` | `typecheck` | `typecheck` |
| `python-bandit` | `security_analysis` | `security` |
| `python-pip-audit` | `dependency_audit` | `audit` |

For example, the lint command is
`<DevPython> <Tools>/python-qa/qa.py --project-root <Repo> --python <DevPython> lint`.
Use `versions` as the launcher health check; verify useful operations separately.
Register Git, `gh` and `rg` if the selected PF workflow resolves them through its
tool registry. Registration describes a tool; it does not install or test it.

## 5. MCP and the agent host

Install/configure each server in the **actual host used by the contributor**.
PF `mcp-register` is workplace metadata and does not connect the host by itself.
Preserve unrelated host entries; keep executable paths and secret references in
local configuration. Use absolute executable paths so GUI hosts do not depend on
an interactive shell's PATH.

| Component | Setup and readiness |
| --- | --- |
| **Serena or an equivalent IDE MCP** | Preferred for symbol lookup and references before repository-wide text search. Current upstream installation: `uv tool install -p 3.13 serena-agent==2.1.0`, then `serena init`; uv manages its separate tool interpreter. Configure host-owned stdio command `serena start-mcp-server --project <Repo>`. Read server instructions, select the correct project and successfully inspect a real Python symbol. See [official installation](https://oraios.github.io/serena/02-usage/010_installation.html) and [running guide](https://oraios.github.io/serena/02-usage/020_running.html). If an older working server is present, inspect it before replacement. |
| **PF MCP** | Optional transport for the required local PF workflow; native CLI also works. In Codex, run `<PfPython> <Core>/bin/pf.py codex-mcp install --workplace <Workplace> --distribution-root <Core> --python <PfPython>` to inspect the plan, then add `--apply` for the requested setup. Inspect `codex-mcp status`, reload the real host, and confirm PF tools and `pf.actions.list` are available. See [host integration](../getting-started/runtime-autostart.md#codex-mcp-registration). |
| **Playwright MCP** | Prepare for browser/UI/documentation checks. Install a supported Node.js LTS, then `npm install --prefix <Tools>/browser-mcp --save-exact @playwright/mcp@0.0.85`. Run `node <Tools>/browser-mcp/node_modules/playwright/cli.js install chromium`. Configure the Chromium JSON file below. Host stdio command: `node`, args: `<Tools>/browser-mcp/node_modules/@playwright/mcp/cli.js --config <Tools>/browser-mcp/pf-browser.json`. Verify navigation to a local test page and a readable snapshot. On Linux install browser system dependencies using Playwright's documented installation flow. See [official instructions](https://github.com/microsoft/playwright-mcp). |
| **Context7** | Optional additional documentation source after local packages. Configure the host's remote HTTP MCP URL `https://mcp.context7.com/mcp`; if an API key is used, map it from a local secret/environment to the Authorization header. Do not commit a literal key. Verify library resolution and one documentation query. See [official configuration](https://context7.com/docs/resources/all-clients). |
| **Chrome/Firefox DevTools** | Optional diagnostics for a specific need. Playwright is the first browser check backend; an unavailable DevTools server does not block unrelated work. |

Save this local Playwright configuration as `<Tools>/browser-mcp/pf-browser.json`:

```json
{
  "browser": {
    "browserName": "chromium",
    "isolated": true,
    "launchOptions": { "headless": true }
  }
}
```

Install uv through its [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/)
if it is missing. The Serena and Playwright versions above were checked against
upstream metadata during this guide's preparation; review newer versions before
changing the workstation baseline and record what was actually installed.
After connecting a server, register needed PF capabilities with `mcp-register`
using a secret-free command and the actual transport. A stored configuration or
a process launch is not proof of a connected MCP session.

PF Runtime, App Server autostart, Director, hooks and Ledger sessions are separate
product facilities. This contributor setup does not install services or require
them unless the selected process requires those capabilities. PHP/Joomla, marketing packages and generic
frontend build stacks are not dependencies of PF Core development.

## 6. Initialize local project PF and select the task source

Inspect an existing `.pf` before onboarding; preserve valid local history and
use its exact continuation. For a fresh clone, select a task-appropriate process
from the active development pack (for example `software-feature-development` or
`bug-fix`). With explicit paths, preview then apply:

```sh
<PfPython> <Core>/bin/pf.py project-onboard --project-root <Repo> --workplace <Workplace> --type processforge-development --process <process-id> --coordination-mode simple --dry-run
<PfPython> <Core>/bin/pf.py project-onboard --project-root <Repo> --workplace <Workplace> --type processforge-development --process <process-id> --coordination-mode simple --apply
<PfPython> <Core>/bin/pf.py doctor-project --project-root <Repo>
<PfPython> <Core>/bin/pf.py project-context-check --project-root <Repo>
```

Use `processforge-development` for this source checkout so PF can distinguish it
from an accidental onboarding of an installed Core. `simple` is the initial
coordination choice; select a more involved mode only with its required services.
Read the onboarding plan. Entry generation preserves shared text but can append a
managed startup block to root AGENTS; inspect that local diff and do not include
generated entry changes in an unrelated task PR. Never use `--force` to bypass an
entry conflict. Context/doctor failures must be resolved before substantive Work.

Apply the [collaboration profile](collaboration-profile.json) to supplemental
`project.collaboration` fields, keeping the actual local project identity. The
default is `local_pf` for 1.3.0. Read [both task workflows and link fields](task-collaboration.md).
For `github` mode, read/create the issue before starting its Work. For `local_pf`,
an issue may be created later when publishing a substantial task or result.

Select the required knowledge ids and actual tools/MCP capabilities in local
context requirements; run `project-context-refresh` and `project-context-check`
after deliberate configuration changes. For native search, use `search-index
refresh` and `search-index doctor` with explicit project/workplace paths.
Read `pf.context`, then create/resume the exact Work, read its assignment/capsule
and supplemental links, and follow `pf.work.state` / `pf.work.transition` through
the selected process. With CLI, inspect the installed action's help/schema for
equivalent commands; do not invent `pf.work.start` arguments for supplemental fields.
Keep root `.pf` ignored and private. A clean source-validation checkout can remain
without `.pf`; contributors initialize their own local state after cloning.

## 7. Updates and readiness evidence

The package `update_sites` point to each canonical repository's
`releases/latest/download/<manifest>.json`. Version-specific ZIP URLs and SHA-256
protect the selected payload. Use the native PF sequence:

```sh
<PfPython> <Core>/bin/pf.py update entity-sources rebuild --workplace <Workplace>
<PfPython> <Core>/bin/pf.py update candidates refresh --workplace <Workplace>
<PfPython> <Core>/bin/pf.py update candidates list --workplace <Workplace>
<PfPython> <Core>/bin/pf.py update stage --workplace <Workplace> --candidate <id>
<PfPython> <Core>/bin/pf.py update verify --workplace <Workplace> --candidate <id>
<PfPython> <Core>/bin/pf.py update apply --workplace <Workplace> --candidate <id> --confirm
```

Read the changelog and intended destination before applying. Preserve backups
and verify package resolution afterwards. Package updates save the selected
installed-subject record beside the payload backup. `update rollback` restores
that record (including prior absence) while preserving other registry entries.
Conflicting selected metadata and legacy backups without a metadata preimage
are refused; preserve those backups for explicit recovery. A failed payload or
metadata operation is not a completed rollback: retain its receipt and retry
only through the supported guarded path. Verify both payload and registry versions
before checking for another update.

Before declaring the device ready, record source/Core revisions, interpreter and
tool versions, package versions/hashes, actual directories, passed doctor checks,
MCP connection results and any unavailable capabilities. Keep this device report
private. From the source checkout run schema, checksum and public-cleanliness
checks from CONTRIBUTING, plus a relevant existing smoke and scoped QA when code
is changed. Use real Windows and Linux execution, including CI runners, for
applicable executable changes; a skipped or missing platform check is a limit.
Deliver source changes through a working branch, PR to `dev`, review/checks,
permitted merge and verified GitVerse mirror.
