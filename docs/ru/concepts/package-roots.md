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
