# Full Resource Authoring Chain

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.joomla.local --title "Local Joomla Documentation" --package-root global --apply
python bin/pf.py platform-create --workplace ./workplace --id platform.joomla --title "Joomla Platform" --project-type joomla-component --knowledge-package docs.joomla.local --template report.audit.basic --apply
python bin/pf.py project-onboard --project-root ./project --workplace ./workplace --type joomla-component --apply
```

The project snapshot should include `platform.joomla`, `docs.joomla.local`, and `report.audit.basic`.
