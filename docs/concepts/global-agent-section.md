# Global Agent Section

ProcessForge does not own a workplace-level `AGENTS.md`, `CODEX.md`, or similar
agent instruction file. It inserts or updates only a bounded section.

Markers:

```markdown
<!-- PROCESSFORGE:START -->
...
<!-- PROCESSFORGE:END -->
```

The bounded section tells agents when ProcessForge applies and points them to
the project-local flow entrypoint:

1. `.pf/AGENTS.md`
2. `.pf/process-forge.yaml`
3. `.pf/contexts/project-context.snapshot.md`

Existing user instructions outside the markers are preserved. Re-running the
operation is idempotent.

## Agent-Specific Snippets

Agent-specific files such as `CODEX.md`, `CLAUDE.md`, `GEMINI.md`, and
`.cursor/rules` should use the same short adapter idea:

```markdown
When ProcessForge applies, read `.pf/AGENTS.md`, `.pf/process-forge.yaml`, and
`.pf/contexts/project-context.snapshot.md`. Follow assignment boundaries and
write session telemetry.
```

These snippets complement the global section; they do not replace local agent
or device instructions.

Use:

```bash
python tools/processforge.py global-agents-section --path <agent-file> --dry-run
python tools/processforge.py global-agents-section --path <agent-file> --force
```
