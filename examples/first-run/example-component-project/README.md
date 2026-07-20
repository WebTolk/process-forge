# Example Component Project Onboarding

Onboard a component-like project after the workplace exists:

```bash
python bin/pf.py project-onboard --project-root ./example-component --workplace ./pf-workplace --type example-component --apply
python bin/pf.py doctor-project --project-root ./example-component
```

For a strict workflow, create or register the required package before the
platform contract:

```bash
python bin/pf.py knowledge-package-create --workplace ./pf-workplace --id docs.example --title "Example Documentation" --package-root global --apply
python bin/pf.py platform-create --workplace ./pf-workplace --id platform.example --title "Example Platform" --project-type example-component --knowledge-package docs.example --apply
python bin/pf.py platform-contract-doctor --workplace ./pf-workplace --platform platform.example
```

Project onboarding must report missing required platform contracts instead of
silently guessing. Heavy documentation and source snapshots should be
referenced through `knowledge_roots.local-docs`, not copied into the project.
