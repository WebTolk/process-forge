# Development snapshot: Python quality and safer project setup

This development snapshot retains the 1.2.0 base version and adds the following
accepted-source changes. It is not a new stable publication.

- A portable workplace Python QA bundle: Ruff, pytest, pytest-cov, coverage.py,
  mypy, Bandit and pip-audit, with pinned versions and a shared launcher for
  different projects. Development dependencies remain outside PF Runtime.
- Required test and code-quality evidence in the existing software-development
  assurance stage, with persistent project instructions and shared QA tool
  requirements. Existing active Runs retain their pinned process definitions.
- Read-only no-selector `context-resolve`, including valid `--json` output.
  It returns the existing canonical snapshot and readiness check without
  overwriting legacy context files. Scripts depending on the old implicit write
  should use the explicit modern snapshot workflow. Resource-selector resolution
  and explicit writers retain their existing behavior.
- Automatic project-local Codex hook configuration during shared CLI/MCP project
  initialization when the actual workplace/device is Forge. Project file-only
  mode does not suppress this setup. Existing settings and custom hooks are
  preserved; repeated initialization is idempotent and failures are reported.

The current trusted native hook adapter is Codex (`codex-hooks.v1`). Claude Code,
Cursor and Gemini CLI do not yet have registered native PF hook adapters and are
reported as unsupported rather than receiving invented configurations. Existing
projects are not silently rewritten by a Core update. Agent hosts may require
reload after their hook configuration changes; see the initialization report.

New behavior has focused unit/regression and local ingress tests. Source,
packaged, installed CLI and actually loaded Runtime/MCP evidence remain separate.
See [Python quality](../guides/python-quality.md),
[context resolution](../guides/context-resolve.md) and
[Forge initialization hooks](../guides/forge-init-hooks.md).
