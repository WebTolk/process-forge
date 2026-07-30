# Platform Contract Example

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py platform-create --workplace ./workplace --id platform.example-app --title "Example Application Platform" --project-type example-app --requires-package docs.example-domain --apply
python bin/pf.py platform-contract-doctor --workplace ./workplace --platform platform.example-app
```

Create or register dependencies first, then create the platform contract. Use `--requires-package`, `--recommends-package`, `--optional-package`, and the matching template/tool/MCP flags to link existing resource ids.
