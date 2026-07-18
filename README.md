# ProcessForge

**Russian documentation:** [README.ru.md](README.ru.md)

ProcessForge is a file-first process framework for AI-assisted project work.
It stores process definitions, runs, tasks, iterations, artifacts, reviews,
handoffs, knowledge packages, templates, and platform contracts in versionable
project and workplace files.

ProcessForge does not require a backend, database, web UI, network transport,
or mandatory long-running runner. The current release is Python-first and uses
short-lived CLI commands by default.

Current release candidate: `0.1.0-rc.1`.

![ProcessForge architecture](docs/assets/processforge-architecture.svg)

## What ProcessForge Is

ProcessForge gives people and AI agents a shared operational layer for project
work. Instead of keeping process rules only in chat, ad hoc notes, or a single
README, ProcessForge records the work model in files that can be reviewed,
versioned, checked, and handed off.

It is useful when a project needs repeatable workflows, explicit tasks, durable
agent context, project-local instructions, and release checks that can run
without a central service.

## Core Concepts

- Distribution root: the ProcessForge tool checkout or unpacked release.
- Workplace: machine-level resources such as shared knowledge packages,
  reusable templates, platform contracts, registries, and defaults.
- Project: a normal repository connected to a workplace through a `.pf/` folder.
- `.pf/START_AGENT_HERE.md`: the project-local entrypoint an agent should read
  after onboarding.
- Process definition: a YAML file that describes stages, roles, artifacts,
  gates, events, tools, and evolution policy.
- Run, task, iteration: the execution record for a work session, its tasks, and
  repeated work/debug/fix/review attempts.
- Authoring parity: a check that existing process definitions can be backfilled
  into authoring answers and reproduced semantically.

ProcessForge differs from a plain README or `AGENTS.md` because it does not only
describe conventions. It creates a project flow layer with structured process
definitions, runtime records, checks, and artifacts.

## Installation

Clone or unpack ProcessForge once as a tool:

```bash
git clone <processforge-repo> process-forge
cd process-forge

python bin/pf.py version
python bin/pf.py release-test --root .
```

Use `python bin/pf.py` from the distribution root. After a project is onboarded,
use `python .pf/runtime/bin/pf.py` inside that linked project.

## Quick Start

Initialize a workplace:

```bash
python bin/pf.py workplace-init --workplace ../pf-workplace --apply
python bin/pf.py doctor-workplace --root ../pf-workplace
```

Onboard a project:

```bash
python bin/pf.py project-onboard --project-root ../my-project --workplace ../pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Inside the onboarded project:

```bash
cd ../my-project
python .pf/runtime/bin/pf.py doctor-project --project-root .
python .pf/runtime/bin/pf.py run-create --project-root . --id first-run --title "First ProcessForge run" --process task-batch-execution --apply
```

See [QUICKSTART.md](QUICKSTART.md) for the complete short path.

## Using ProcessForge With AI Agents

Do not copy the whole ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders.

Install ProcessForge once as a tool, initialize a workplace, onboard the
project, and add a short instruction to the agent configuration that points to
the ProcessForge installation and tells the agent to read
`.pf/START_AGENT_HERE.md` for project-specific instructions.

Generate the project start prompt:

```bash
python bin/pf.py agent-start-prompt --project-root ../my-project
```

Prompt snippets for common tasks are in
[docs/getting-started/agent-prompts.md](docs/getting-started/agent-prompts.md).

## First-Run Commands

```bash
python bin/pf.py workplace-init --workplace <workplace-path> --apply
python bin/pf.py doctor-workplace --root <workplace-path>
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-path> --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root <project-root>
```

Compatibility commands still exist for older scripts, but new documentation and
new projects should use `workplace-init` and `project-onboard`.

## Creating Workplace Resources

Reusable template:

```bash
python bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>
```

Knowledge package:

```bash
python bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Platform contract:

```bash
python bin/pf.py platform-create --workplace <workplace-path> --id <platform-id> --title "<title>" --apply
python bin/pf.py platform-contract-doctor --workplace <workplace-path> --platform <platform-id>
```

## Creating Custom Processes

Inside an onboarded project, use the project runtime launcher:

```bash
python .pf/runtime/bin/pf.py process-authoring-start --project-root . --id <process-id> --title "<title>" --scope project --kind operational --apply
python .pf/runtime/bin/pf.py process-authoring-review --project-root . --id <process-id>
python .pf/runtime/bin/pf.py process-authoring-apply --project-root . --id <process-id> --apply
python .pf/runtime/bin/pf.py process-doctor --project-root . --process <process-id>
```

For one-command examples from the distribution root:

```bash
python bin/pf.py process-create --project-root ../my-project --answers examples/process-authoring/seo-audit/answers.yaml --apply
```

## Running Task Batches

Inside an onboarded project:

```bash
python .pf/runtime/bin/pf.py run-create --project-root . --id <run-id> --title "<title>" --process task-batch-execution --apply
python .pf/runtime/bin/pf.py task-create --project-root . --run <run-id> --id <task-id> --title "<task title>" --process <process-id> --apply
python .pf/runtime/bin/pf.py iteration-add --project-root . --task <task-id> --kind work --summary "..." --apply
python .pf/runtime/bin/pf.py task-complete --project-root . --task <task-id> --summary "..." --apply
python .pf/runtime/bin/pf.py run-summary --project-root . --run <run-id> --apply
python .pf/runtime/bin/pf.py run-doctor --project-root . --run <run-id>
```

## Release Checks

From the ProcessForge distribution root:

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
python bin/pf.py release-pack --root . --output dist/processforge-v0.1.0.zip
python bin/pf.py release-archive-test --archive dist/processforge-v0.1.0.zip
```

## Documentation Map

- [Quickstart](QUICKSTART.md)
- [Documentation index](docs/index.md)
- [Installation](docs/getting-started/installation.md)
- [First run](docs/getting-started/first-run.md)
- [Agent prompts](docs/getting-started/agent-prompts.md)
- [Workplace vs project](docs/concepts/workplace-vs-project.md)
- [Runs, tasks, and iterations](docs/concepts/runs-tasks-iterations.md)
- [Authoring parity](docs/authoring/authoring-parity.md)
- [Known limitations](docs/known-limitations.md)

## Known Limitations

Version `0.1` is a file-first MVP. The watcher, runner/orchestrator service,
GUI, marketplace, remote sync, and database-backed control plane are outside
this release. Resource parity for templates, knowledge packages, and platform
contracts is intentionally shallow and reports WARN until full authoring
round-trips exist.

## License

See [LICENSE](LICENSE).
