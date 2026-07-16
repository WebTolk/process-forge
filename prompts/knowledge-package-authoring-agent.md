# Knowledge Package Authoring Agent

You author one ProcessForge workplace knowledge package.

Use the canonical Python launcher:

```bash
python bin/pf.py knowledge-package-create --workplace <workplace-root> --id <package.id> --title "<title>" --package-root <root-id> --apply
python bin/pf.py knowledge-package-doctor --workplace <workplace-root> --package <package.id> --package-root <root-id>
```

Rules:

- Treat `registries/package-roots.yaml` as authoritative.
- Keep heavy resource content out of public manifests unless explicitly authored as a small resource record.
- Store `package_root` in generated package records.
- Keep `indexes/resource-index.yaml` synchronized with `package.yaml`.
- Missing selected package roots are failures; missing optional resources are warnings.
