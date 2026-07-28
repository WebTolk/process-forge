# Initialization Order

Use this order for a new ProcessForge installation, workplace, and project:

1. Install ProcessForge distribution.
2. Verify ProcessForge itself.
3. Run guided workplace setup by default for human-led setup, or direct
   `workplace-init` only for explicit automatic setup.
4. Configure path constants and roots.
5. Configure knowledge roots, especially local documentation roots.
6. Register tools and MCP servers.
7. Create or import knowledge packages.
8. Create reusable templates.
9. Create platform contracts.
10. Onboard project.
11. Create run/task workflow.
12. Create custom processes as needed.

## Why Platform Contracts Come Later

Platform contract is not a primary resource. It is a composition over existing packages, templates, tools, MCP servers, processes, coding standards, and capabilities.

Do not start by creating a platform contract if its required packages, templates, or tools do not exist yet. Create or register the dependencies first, then create the platform contract.

Do not onboard a project until the workplace exists and the required workplace
resources are created, registered, validated, or explicitly out of scope.

Base languages and web technologies are part of those dependencies. Model them
as knowledge packages and capabilities, then include them from the platform
contracts that need them.

Heavy local documentation and source trees stay outside public package manifests. Reference them through `knowledge_roots.local-docs` and package resources that use `path_ref`.

## Agent Environments

Do not copy the whole ProcessForge repository into `.codex`, `.claude`, `.agents`, or similar agent configuration folders.

Install ProcessForge once as a tool, initialize a workplace, and add a short instruction to the agent configuration telling it where ProcessForge is installed and that project-specific instructions live in `.pf/START_AGENT_HERE.md`.
