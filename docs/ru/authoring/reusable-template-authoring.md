# Reusable template authoring

Reusable template — это общий шаблон, который можно использовать в разных
проектах через workplace.

Создайте шаблон из distribution root:

```bash
python bin/pf.py template-create --workplace <workplace-path> --id <template-id> --title "<title>" --apply
python bin/pf.py template-doctor --workplace <workplace-path> --template <template-id>
```

Хороший шаблон должен иметь понятный id, назначение, входные параметры,
ожидаемые outputs и пример использования. Не храните в публичном шаблоне
приватные абсолютные пути.
