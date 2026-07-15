# Workplace Configuration

Use Workplace Init when setting up a machine or runner host for ProcessForge.

## Answers File

Start from:

```text
templates/workplace-init.answers.yaml
```

Set:

- workplace id
- workplace name
- type
- operating system
- root path
- optional knowledge roots
- optional package roots
- optional template roots
- optional tools root
- optional MCP root

## Apply

```bash
python tools/processforge.py init-workplace --root <workplace-root> --answers <answers.yaml> --apply
```

## Verify

```bash
python tools/processforge.py doctor-workplace --root <workplace-root>
```
# Path Constants

Define reusable path bases in `workplace.yaml`:

```yaml
path_constants:
  PF_WORKPLACE: "."
  PF_KNOWLEDGE: "knowledge"
  PF_TEMPLATES: "reusable-templates"
  PF_TOOLS: "tools"
```

Registry entries may use `${PF_KNOWLEDGE}/joomla/docs` or an explicit absolute path. Absolute paths are allowed in workplace/private files, but never in public project snapshots.

Run `python tools/processforge.py path-resolve --workplace <workplace-root> --path "${PF_KNOWLEDGE}/joomla/docs"` to inspect expansion.
