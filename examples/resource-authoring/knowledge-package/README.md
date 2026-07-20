# Knowledge Package Example

```bash
python bin/pf.py workplace-init --workplace ./workplace --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.example-domain --title "Example Domain Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.example-domain --package-root global
```

The generated package contains `package.yaml` and `indexes/resource-index.yaml`.

Base language and web-technology knowledge follows the same package pattern:
create knowledge packages and capabilities first, then include them from the
platform contract that needs them.
