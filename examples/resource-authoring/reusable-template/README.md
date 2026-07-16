# Reusable Template Example

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py template-doctor --workplace ./workplace --template report.audit.basic
```

The generated template is registered in `registries/templates.yaml` and can be referenced by a platform contract.
