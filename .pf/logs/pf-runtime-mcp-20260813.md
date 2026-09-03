# PF Runtime MCP Architecture Log

## 2026-08-13T14:00:00+04:00 - codex-main - setup

- task: Master prompt for local ProcessForge Runtime, agent events, and unified MCP interface.
- files analyzed: `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/contexts/project-context.snapshot.yaml`, `задания/Мастер-промпт_ локальная служба Process Forge, события агентов и единый MCP-интерфейс.md`.
- status: planning-only task created and started under run `pf-runtime-mcp-20260813`.
- follow-up: project context is currently broken; report must surface it.

## 2026-08-13T14:10:00+04:00 - codex-main - local architecture audit

- files analyzed: `docs/concepts/hooks-events.md`, `docs/concepts/processforge-events.md`, `docs/concepts/session-telemetry.md`, `docs/concepts/tool-mcp-registration.md`, `docs/concepts/runtime-model.md`, `docs/concepts/agent-session-model.md`, `docs/concepts/runtime-drivers.md`, `.pf/hooks.yaml`, `schemas/event-envelope.schema.json`, `schemas/process-event.schema.json`, `schemas/hooks.schema.json`, `schemas/mcp-registry.schema.json`, selected regions of `tools/processforge.py`.
- status: existing file-first runtime, event append, hook outbox, context resolution, agent ledger, runtime driver, worker-run, and MCP registry surfaces identified.
- follow-up: no product code changes before report approval.

## 2026-08-13T14:25:00+04:00 - codex-main - external hook review

- files or sources analyzed: Claude Code hooks docs, Gemini CLI hook docs, OpenAI Codex public repository and hook-related issues/discussions, Kimi CLI public repository/discussion search.
- status: Claude and Gemini have documented hook contracts; Codex hook surface appears evolving; Kimi stable hooks were not confirmed.
- follow-up: PoC should use generic stdin adapter plus documented Gemini/Claude mappings unless user chooses Codex dogfooding first.

## 2026-08-13T14:35:00+04:00 - codex-main - report written

- files changed: `.pf/artifacts/pf-runtime-mcp-20260813/architecture-report.md`, `.pf/logs/pf-runtime-mcp-20260813.md`, `.pf/handoffs/pf-runtime-mcp-20260813-handoff.md`.
- status: architecture report prepared with required sections A-L.
- follow-up: run task completion and validation commands.
