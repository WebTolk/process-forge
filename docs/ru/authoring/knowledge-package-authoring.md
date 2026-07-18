# Knowledge Package Authoring

Knowledge package собирает документацию, заметки, ссылки и resource index,
которые агент может использовать при работе над проектами.

```bash
python bin/pf.py knowledge-package-create --workplace <workplace-path> --id <package-id> --title "<title>" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace <workplace-path> --package <package-id>
```

Пакет должен ссылаться на ресурсы переносимо: через ids, относительные пути или
private registry, если источник привязан к конкретной машине.
