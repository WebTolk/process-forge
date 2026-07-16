# Resource Authoring

Resource authoring creates reusable workplace assets before they are selected by projects.

The MVP includes three authoring processes:

- `reusable-template-authoring`
- `knowledge-package-authoring`
- `platform-contract-authoring`

Use the Python launcher from this checkout:

```bash
python bin/pf.py template-create --workplace ./workplace --id report.audit.basic --title "Basic Audit Report" --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.joomla.local --title "Local Joomla Documentation" --package-root global --apply
python bin/pf.py platform-create --workplace ./workplace --id platform.joomla --title "Joomla Platform" --project-type joomla-component --knowledge-package docs.joomla.local --template report.audit.basic --apply
```

Inside an onboarded project, use the project-local launcher:

```bash
python .pf/runtime/bin/pf.py project-context-refresh --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Project onboarding reads `project_type_hints` from platform contracts. When a contract declares a matching hint, the project context snapshot records the selected platform, linked knowledge packages, and linked templates without copying their payloads into the project.
