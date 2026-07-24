# Guided Workplace Setup Minimal Example

This neutral example shows the file-first setup flow without real platform ids or machine-local paths.

Run from a ProcessForge checkout:

```bash
python bin/pf.py workplace-setup start --workplace <workplace-root> --session-id first-machine --answers examples/guided-workplace-setup/minimal/answers.yaml --apply
python bin/pf.py workplace-setup review --workplace <workplace-root> --session-id first-machine
python bin/pf.py workplace-setup apply --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup status --workplace <workplace-root> --session-id first-machine
```

The setup session is stored under `<workplace-root>/.pf-workplace/setup-sessions/first-machine/`.
