# Batch knowledge addition: реализация contributor

Статус: `ready_for_review`; зарегистрированная QA не выполнялась.

## READ_ACK и границы

Фактический READ_ACK выдан до анализа и исправления реализации. Прочитаны
замороженные `batch-design-r7.md`, `python-oop-guidance.md` и
`python-source-excerpts.md`; SHA256 всех трёх файлов совпали с prepared input.
Продолжена существующая реализация предыдущей попытки в тех же owned-файлах.

Работа ограничена четырьмя разрешёнными product/test-файлами и собственными
artifacts/log/scratch. Git, PF lifecycle, инфраструктурные действия, live imports,
внешние workplace и subagents не использовались.

## Поведение

- Весь envelope проверяется до native authoring: schema 1, непустой список
  inline-records, отсутствие повторных explicit ID после native-нормализации.
- Default и `--dry-run` не вызывают commit/index; конфликт с `--apply` отклоняется.
  Команда не создаёт отсутствующий пакет и не скачивает URL-источники.
- Каждый applied item подготавливается непосредственно перед собственным
  native preflight/execute; следующий builder видит последние изменения manifest.
  Manifest, resource-index, private registry и audit/recovery остаются у native
  authoring owner.
- Обычные ошибки становятся строками результата в исходном порядке. Успех
  подтверждается только journal-state `committed_audit_complete`. Ошибка после
  commit не выдаётся за успешное добавление; evidence остаётся native recovery.
- KeyboardInterrupt/SystemExit распространяются, кроме legacy `SystemExit`
  с префиксом `FAIL:` на границе builder/явного preflight.
- Успешные catalogue ID формата `package:resource` дедуплицируются с сохранением
  порядка. После всех items вызывается один injected callback `run_resources`.
  При пустой выборке вызова нет. Ошибка индексации сохраняет успешные строки и
  committed additions, но даёт отдельный error и ненулевой CLI exit.
- Отчёты проецируют ограниченные поля и переносимые error codes. Raw exception
  diagnostics и native stdout/stderr не попадают в новый CLI-отчёт. Selected
  indexing всегда отмечено `workplace_reconciled: false`.

## API для primary

`KnowledgeBatchService` принимает `build_plan`, `preflight_plan`, `execute_plan`
и `index_resources`. Builder сохраняет существующий native tuple:
`(plan, resource, result, manifest_path, index_path, package_root)`.
`run(envelope, package_id=..., apply=False, dry_run=False)` хранит состояние
конкретной операции локально и возвращает portable dict.

`KnowledgeBatchCommand(service_factory=...)` конструирует сервис на вызов;
`register_knowledge_add_batch(add_parser, execute=...)` регистрирует parser.
Main wiring и реализация canonical `run_resources` принадлежат primary.

## Проверки и ограничения

Выполнена только разрешённая локальная stdlib-проверка копий собственных файлов:
`python -I -S -B check_sources.py` в owned scratch, Python 3.14.3, exit 0.
Для четырёх файлов прошли `ast.parse` и `compile` без выполнения code objects;
строк длиннее 88 символов не обнаружено. PF-модули не импортировались.
Evidence: `stdlib-source-check.json`; исходник проверки: `check_sources.py`.

Копии проверенных исходников в owned scratch сохранены как evidence точных
байтов. Автоматическая проверка отклонила составную команду с рекурсивной
очисткой (`blocked by policy`, без уточнения причины). Проверка затем выполнена
отдельно без удаления; очистка не заявляется.

В тестовом файле определён 31 сценарий; ни один поведенческий тест здесь не
запускался. Pytest, Ruff lint/format и mypy не запускались. Native fixtures
используют синтетический distribution с упрощёнными схемами для проверки
транзакций; это не проверка полноты release-схем.

Primary должен выполнить зарегистрированную QA на интегрированном кандидате,
проверить выбранную SQLite-замену без чтения чужих bodies, pending/global failure,
unknown ID, busy writer и независимое финальное review. CODE GO, commit/push
и publication не входят в результат contributor.
