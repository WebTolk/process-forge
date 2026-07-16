# Knowledge Package Example

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.joomla.local --title "Local Joomla Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.joomla.local --package-root global
```

The generated package contains `package.yaml` and `indexes/resource-index.yaml`.
