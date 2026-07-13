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
