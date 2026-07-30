# Full Resource Authoring Chain

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py platform-create --workplace ./workplace --id platform.example-app --title "Example Application Platform" --project-type example-app --requires-package docs.example-domain --optional-template report.audit.basic --apply
python bin/pf.py project-onboard --project-root ./project --workplace ./workplace --type example-app --apply
```

The project snapshot should include `platform.example-app`, `docs.example-domain`, and `report.audit.basic`.

Private local docs and source trees belong behind workplace knowledge roots and package `path_ref` records.
