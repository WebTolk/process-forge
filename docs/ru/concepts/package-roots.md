# Package Roots

Package roots определяют, где ProcessForge ищет и записывает knowledge
packages. Обычно есть общий workplace root и при необходимости project-local
root.

Создание пакета:

```bash
python bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Если один package id найден в нескольких roots, write-команды должны получать
явный `--package-root`.

Тяжёлые documentation и source trees не копируются в package manifests или package indexes. Public package YAML должен использовать `path_ref`, особенно `registry: knowledge_roots` и `id: local-docs`, для private local documentation roots.

Package manifests должны оставаться переносимыми. Не записывайте private absolute paths вроде пользовательских home directories или machine-local drive paths в public package/index YAML.
