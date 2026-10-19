# Отчёт transfer

Статус: **passed**.

Создан `src/processforge_core/maintenance/transfer.py` с `UpdateTransferService(distribution_root: Path)`. Служба использует существующие `UpdateSitePolicy` и `UpdateDocumentReader`.

| Исходный алгоритм | Метод | full_ast_equal | signature_equal | annotations_equal |
|---|---|---|---|---|
| `fetch_update_manifest` | `manifest` | true | true | true |
| `copy_or_download_update_artifact` | `artifact` | true | true | true |

Допустимые замены ограничены именами функций, добавлением `self` и обращениями к конкретным владельцам через `self.site_policy` и `self.documents`. Литералы полностью совпадают. Отдельных переносимых констант в этой области нет.

Сохранены таймауты 15/30, модульный импорт `urlopen`, порядок открытия ресурсов, имена файлов, предупреждения и ошибки. Разбор текста manifest остаётся вне `try`; ошибки artifact распространяются с прежней семантикой частичной записи.

Компиляция выполнена без импорта продуктовых модулей. Пять синтетических сценариев выполнены однократно, все passed:

- локальный manifest: live reads и неизвестные поля;
- HTTP manifest: перехват ошибки UTF-8 и timeout 15;
- HTTP manifest: распространение ошибки парсера после закрытия response;
- локальный artifact: `copy2`, имя назначения и распространение ошибки;
- HTTP artifact: timeout 30, порядок контекстов и сохранение частичных данных.

Замороженные зависимости `maintenance/documents.py` и `maintenance/sites.py`: `raw_equal=true`, `ast_equal=true`. Все required-source pins совпали.

SHA-256 продукта:

```text
19f30f95e35772aa0780e62fbd01ebb9fff475d9800dae3cd5591081552f98a8
```

Доказательства находятся в разрешённой области:

- `.pf/artifacts/pf121-oop-core-catalog-transfer-20261018/transfer/proof.json`
- `.pf/artifacts/pf121-oop-core-catalog-transfer-20261018/transfer/normalized-ast.json`
- `.pf/artifacts/pf121-oop-core-catalog-transfer-20261018/transfer/log.md`
- `.pf/tmp/p121-core-catalog-transfer/transfer/verify.py`

Точная Work подтверждена как `implementation`, контекст valid/ready, блокировок нет. Синтетическое выполнение использовало изолированные определения классов без запуска конструкторов зависимостей; конкретные алгоритмы policy/path/parser сохранены. Проверки default composition, реальных scratch-файлов, copied Core, native scripts и миграция Main остаются за primary. Git, инфраструктура и lifecycle не изменялись.
