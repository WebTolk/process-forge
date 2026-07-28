# Path constants

Path constants задают переносимые имена для важных путей. Они помогают не
записывать приватные абсолютные пути в публичные файлы.

Используйте path refs для ресурсов, которые могут находиться в разных местах на
разных машинах. Если путь приватный, держите его в private registry или локальном
config, а не в публичной документации и release files.

Внутри подключенного проекта команды должны использовать project root и
runtime launcher:

```bash
python .pf/runtime/bin/pf.py project-context-check --project-root .
```
