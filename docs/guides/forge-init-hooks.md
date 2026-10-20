# Agent hooks during Forge project initialization

Project initialization automatically prepares supported project-local hooks when
the linked workplace's `coordination.default_project_mode` is `organized` (Forge).
Both `project-init`/`project-onboard` and `pf.project_initialization.initialize`
use the same Core workflow. The existing apply acknowledgement is required.
Dry-run only shows the plan, including `.codex/hooks.json` when applicable.

The decision uses the actual workplace reader. The project's
`process_forge.mode: file_only` does not disable setup. Director capability alone
does not select Forge, and a project's explicit `organized` override does not
turn a Garage workplace into Forge. Initialization never changes workplace mode.
Garage keeps its existing optional installation behavior, including its current
`runtime.garage_hooks` collection policy.

## Supported integration

| Agent | Native PF integration | Configuration |
| --- | --- | --- |
| Codex | Existing `codex-hooks` adapter, `codex-hooks.v1` envelope | Project-local `.codex/hooks.json` |
| Claude Code, Cursor, Gemini CLI | No registered native PF hook adapter in this distribution | No hook files generated |

Codex setup reuses the bundled installer and its existing command format
(`py -3` on the currently supported Windows launcher path). It registers
SessionStart, SessionEnd, PostToolUse, UserPromptSubmit, PreCompact, PostCompact,
Stop and SubagentStop. This identifies the supported bundled protocol, not a
claim that every Codex binary version supports or has trusted the hook layer.
No agent binary is installed, detected by guessing a version, or restarted.
Other agents need a bounded native adapter/ingress contract before auto-setup.

## Results and recovery

Initialization reports configured events, changes, any relative backup reference
and reload requirements through its existing `codex_integration` result. Forge
marks this integration required. Missing adapters, invalid JSON, malformed known
event groups, unsafe destinations and conflicting PF handlers produce bounded
`codex_hooks_*` diagnostics. A required setup failure cannot report complete
initialization. Initialization status shows required hooks as repairable or blocked
and includes `initialize` in its existing repair plan.

The existing native merge preserves custom hooks and unrelated settings. The hook
file is outside the normal initializer's force-overwrite map. Repeated unchanged
initialization leaves its bytes and modification time intact. Existing settings
are backed up before replacement; a failed replacement retains the original and
backup. The backup is private native configuration alongside the hook file and
must be kept private with that file. Restore the reported backup if needed,
correct the diagnostic's cause and rerun initialization. A configuration change
between planning and apply aborts setup instead of overwriting newer settings.

Setup does not alter global agent configuration, grant permissions or fix/start
PF services. Native hooks still go through the existing adapter and authenticated
Runtime or file-first Host ingress, with the current project/session binding,
trusted provenance, deduplication and mandatory effective-Forge gatekeeper.
Project coordination overrides still control collection through that policy;
preparing a hook file does not change it.

Host trust and activation remain native host responsibilities. A new/reloaded
Codex session may be needed to observe changed hooks; `/hooks` reports actual
registration. Source fixture event evidence and installed connected-host evidence
are separate checks. MCP host registration is a separate existing operation.
