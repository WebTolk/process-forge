# Отчёт prompts-bound

Статус: **passed** — исправление привязок и статические проверки завершены. Исполнение failed/unrun smoke остаётся за primary.

Assignment: `p121-core-resources-prompts-bound-correct-only-three-existing-smoke-cons`. Стадия: `implementation`. Identity подготовленного входа, durable assignment и immutable capsule совпадают; readiness — `ready`, блокеров нет. Прочитаны и проверены по SHA-256 все 65 закреплённых источников, включая архитектурные документы, Python material, frozen inputs и handoff.

Изменены ровно три продуктовых файла:

- `tools/smoke_prepared_execution_recovery.py`: три `patch.object(core, 'load_task', return_value=task)` заменены на `patch.object(WorkerAssignmentService, 'load', return_value=task)`. Существующие три прямых Core-reader вызова сохранены.
- `tools/smoke_codex_worker_governance.py`: mock перенесён на `WorkerAssignmentService.load`; вызов prompt — на `_worker_assignment_service.render_prompt`. Канонический import и единственный холодный экземпляр добавлены после существующего `import processforge as pf`.
- `tools/smoke_project_local_package_index_detection.py`: сохранён import `build_project_context_snapshot`; удалён только устаревший импорт index-checks. После bootstrap добавлен `KnowledgeResourceIndexService(Path(__file__).resolve().parents[1])`; `project_checks(project, None, None)` получает прежние три аргумента.

Для каждого изменённого файла доказаны `full_ast_equal=true` после обратного применения объявленных замен, `raw_only_declared_changes=true`, `assertions_unchanged=true`, `fixtures_unchanged=true`. Полные exact replacements записаны в `binding_preservation`.

Семь остальных owned products сохранены побайтно относительно binding before-image. Итоговые SHA-256 всех десяти файлов:

| Файл | SHA-256 |
| --- | --- |
| `src/processforge_core/work/worker_assignment.py` | `f22efd43e3aba13da36f2f3ac6adc01f0145141d929f372dd1c327ab2424af22` |
| `tools/pf_runtime/host.py` | `18b1cf9411f78297047b099658227f36d778a1a17460894dbda49be6e71d7c61` |
| `tools/pf_runtime/service.py` | `837bad737c107a1a621937a3aad5d968a9e6a0fabee23283ab4abd82473861e7` |
| `tools/smoke_codex_worker_governance.py` | `8ff2f0583713574dab72e9c3ae38fae528676aa4cc196c762dead5aeede34876` |
| `tools/smoke_continuation_work.py` | `8cf11ac07384d6dd1f54d14e014912f17c9d1d35093c673e06ff3e5a71c4cbcb` |
| `tools/smoke_expected_report_containment.py` | `e013a8e08b247b14271c807c849373ab093a2f5f7c2637ee241a63f36cf847c0` |
| `tools/smoke_prepared_execution_context.py` | `e692f6210d42da2c190fa19cde5c6a08e9651431f06d0b88221a12faccd0ec08` |
| `tools/smoke_prepared_execution_recovery.py` | `86e3705adebbcad60337ba0f00a88c5b76937d031b114d6ebcbfeb95e209e7e3` |
| `tools/smoke_process_run_task_batch.py` | `133b7d182b9dae2ff1f9df7f8e81f9102502c0483ee7ab9198906485ea9f2c84` |
| `tools/smoke_project_local_package_index_detection.py` | `634c851ea9999dd199dfa75281e85d8793db6ceb46fb5a3a925e247b5fd5cbee` |

Выполнена единая статическая AST/raw/assertion/wiring-проверка. Только три изменённых скрипта скомпилированы через `compile` без импортов, исполнения и записи `.pyc`.

Полный word search по `src/tools` охватил 599 текстовых файлов и все двенадцать выбранных исходных имён, включая строки. Обращений к старым реализациям не осталось. Оставшиеся совпадения `path_is_relative_to` проверены как определение, импорты и вызовы канонического `common.paths`, предусмотренного frozen `special_owners`.

Доказательства находятся в `.pf/artifacts/pf121-oop-core-resources-20261018/prompts-bound/proof.json`:

- SHA-256 текущего proof: `836c33a756fdd0602254ed7ebdf49710bbb4f0521170a9f005b8c3357a03985f`.
- Исходный алгоритмический proof: `a9d5d9b51fa36aba33e2a8046e94740f12e0512fef782ba2c4a3dd11a5c34415`.
- Предыдущий bootstrap proof: `fd59b06d37d3a5cba8eaac474e8dd042aed1709beda84c932cc8b281e1e63cdd`.
- `algorithms` и пять `synthetic_cases` сохранены с отметкой `retained_not_rerun`.
- `consumer_preservation` охватывает восемь consumers через композицию предыдущего proof и точных binding deltas.
- `bootstrap_preservation` сохранён; Core/Host/Service этой работой не изменялись.

Повторно не запускались три успешных smoke, 98 parity cases и две проверки import order. Их evidence сохранены. Primary продолжает failed/unrun scripts; новые результаты их исполнения этим отчётом не заявляются.

Бизнес-логика, guards, fixtures, assertion lists и terminal matrix сохранены. Git, инфраструктура, вложенные агенты и lifecycle transitions не использовались. Serena/IDE MCP недоступен; применены локальное чтение и статический поиск.