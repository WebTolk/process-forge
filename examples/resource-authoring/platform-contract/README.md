# Platform Contract Example

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py platform-create --workplace ./workplace --id platform.joomla --title "Joomla Platform" --project-type joomla-component --apply
python bin/pf.py platform-contract-doctor --workplace ./workplace --platform platform.joomla
```

Use `--knowledge-package` and `--template` to link existing resource ids.
