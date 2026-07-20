# Package Roots

Package roots define where knowledge packages are discovered and written.
ProcessForge can work with a project-local package root and one or more shared
workplace roots.

Use package roots when knowledge should be reusable across projects without
copying large documentation trees into each repository.

Create a package from the distribution root:

```bash
python bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Public package manifests should reference resources by ids or portable path
references. Private machine paths belong in private registries, not in public
release files.

Heavy documentation and source trees are not copied into package manifests or package indexes. Public package YAML must use `path_ref`, especially `registry: knowledge_roots` and `id: local-docs`, for private local documentation roots.

Package manifests should stay portable. Do not write private absolute paths such as user home directories or machine-local drive paths into public package/index YAML.
