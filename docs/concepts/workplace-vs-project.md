# Workplace Vs Project

The workplace and project are separate ProcessForge layers.

## Workplace

The workplace belongs to a device, server, or runner host. It stores local registries and resources such as package roots, knowledge roots, tools, MCP providers, templates, and runtime event logs.

The workplace process is `workplace-initialization`.

## Project

The project layer belongs to one concrete repository or working folder. It stores `.pf/`, project context snapshots, assignments, artifacts, reviews, handoffs, hooks, and private runtime data.

The project process is `project-onboarding`.

## Boundary

Project onboarding may reference workplace registries through local config, but it must not recreate the workplace or copy global packages into the project. Public project files must not contain local absolute paths.

## Launchers

ProcessForge is Python-first. The canonical public distribution entrypoint is `bin/pf.py`. Thin optional wrappers may call the same CLI, but public docs should teach the Python launcher first.

A normal linked project does not contain ProcessForge core. It may contain `.pf/runtime/bin/pf.py`, which reads private local config and calls the distribution CLI.

Agent configuration folders such as `.codex`, `.claude`, and `.agents` should only contain a short instruction that tells the agent where ProcessForge is installed and that project-specific instructions live in `.pf/START_AGENT_HERE.md`.

The workplace holds machine-level knowledge packages, reusable templates, tools, MCP servers, platform contracts, and roots such as `knowledge_roots.local-docs`. A project receives a `.pf/` folder from `project-onboard`; it does not receive a copy of the ProcessForge repository or heavy documentation/source trees.
