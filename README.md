# ProcessForge

ProcessForge is a file-first process system for turning repeatable work into governed workflows.

It composes workplace configuration, knowledge packages, tools, MCP servers, reusable templates, project rules, process definitions, task inputs, and agent profiles into executable contexts for AI agents and humans.

## What It Is

ProcessForge is a portable file system for defining and running repeatable work without requiring a server, database, dashboard, or external control plane.

It is suitable for software work, testing, content production, media production, SEO and GEO work, documentation, operations, and other repeatable processes that benefit from explicit stages, artifacts, reviews, handoffs, and logs.

## Core Ideas

- A process is described as files.
- A workplace layer describes what is available on the current machine.
- A project flow layer describes how a specific project works.
- Knowledge packages, tools, templates, and process rules are merged into an execution context.
- Assignments define bounded work for one agent or human.
- Artifacts, reviews, handoffs, and logs make progress durable.
- Process versions are immutable; upgrades are assessed through existing artifacts.

## Repository Layout

```text
process-forge.yaml       Root manifest for this ProcessForge project
AGENTS.md                Agent boot and working rules
docs/                    Concepts, authoring guides, validation docs, examples
schemas/                 JSON schemas for manifests, assignments, artifacts, and reviews
processes/               Seed process definitions
packages/                Seed knowledge package manifests
templates/               Reusable templates for process work
examples/                Starter projects for different domains
assignments/             File-based work assignments
artifacts/               Durable outputs from work stages
contexts/                Execution Context Packages
logs/                    Append-only work logs
reviews/                 Review artifacts
handoffs/                Handoff notes between roles
adr/                     Architecture Decision Records
tools/                   Local validation tools
runtime/                 Optional future local supervisor draft area
```

## Quick Start

1. Copy the ProcessForge directory into a project.
2. Read `AGENTS.md`.
3. Read `process-forge.yaml`.
4. Create or select an assignment in `assignments/`.
5. Create an Execution Context Package in `contexts/`.
6. Work only inside the assignment's allowed file scope.
7. Save outputs in `artifacts/`, `reviews/`, `handoffs/`, and `logs/`.
8. Run the validators from `tools/`.

## Init Commands

ProcessForge can initialize a machine-local workplace layer and a project layer:

```bash
python tools/processforge.py init-workplace --root <workplace-root> --dry-run
python tools/processforge.py init-workplace --root <workplace-root> --apply
python tools/processforge.py doctor-workplace --root <workplace-root>

python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --apply
python tools/processforge.py doctor-project --project-root <project-root>
```

Dry run is proposal-first. Apply mode writes files. Brownfield project init does not overwrite existing files without `--force`; it writes `.candidate` files for conflicts.

## Session And Context Commands

ProcessForge can also start a session, resolve context, compile assignment context, and verify context freshness:

```bash
python tools/processforge.py session-start --mode resume --project-root <project-root>
python tools/processforge.py context-resolve --project-root <project-root>
python tools/processforge.py context-compile --project-root <project-root> --assignment <assignment-path> --capsule
python tools/processforge.py doctor-context --project-root <project-root>
```

Session bootstrap keeps global `AGENTS.md` as a small bootloader. Context resolution creates a Context Index, Resolved Rules, Conflict Report, source fingerprints, and assignment-specific context packages instead of one large prompt.

## MVP Boundaries

The MVP is file-only. It does not require a backend, database, web UI, or runner. Future local supervisor and managed modes are supported by the file model, but they are not required for current use.

The core is not tied to a specific platform, programming language, CMS, or software-development-only workflow.

## Validation

Run the baseline checks:

```bash
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
python tools/processforge.py --help
python tools/processforge.py doctor-context --project-root .
```

See `docs/validation/validation.md` for details.
