# Hooks And Events

ProcessForge writes process and runtime events into project-local files. Hooks
can match those events and write outbox payloads for later delivery.

Events are stored under:

```text
.pf/runtime/events/events.ndjson
```

Hook configuration lives in:

```text
.pf/hooks.yaml
```

Test hook matching from a linked project:

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --dry-run
```

Write an outbox payload:

```bash
python .pf/runtime/bin/pf.py hooks-dispatch --project-root . --event-type assignment.completed --outbox
```

The current file-first runtime writes local files. Network delivery and
long-running event processing are outside the core runtime.
# Codex Runtime adapter

`tools/pf_runtime/codex_hooks.py` is a thin hook adapter. It accepts only the
documented `SessionStart`, `SessionEnd`, and `PostToolUse` facts, normalizes
them, and sends them through the existing Runtime/Core event path. It never
executes hook payload commands, creates tasks, chooses resources, or makes
stage decisions. A hook outside a ProcessForge project is ignored successfully
so observation cannot make Codex unavailable.
