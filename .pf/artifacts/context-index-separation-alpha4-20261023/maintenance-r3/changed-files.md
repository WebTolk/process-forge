# Изменённые файлы maintenance R3

Продукт:

- `src/processforge_core/resources/index_backend.py` — новый structural backend Protocol и factory type.
- `src/processforge_core/resources/index_maintenance.py` — новый canonical maintenance owner.
- `tools/pf_cli/commands/search_index.py` — refresh/rebuild/tick через scoped-операцию owner; constructors, guards и stdout mapping сохранены.
- `tools/pf_cli/commands/search_maintenance.py` — новый явный workplace adapter.
- `tools/pf_cli/parsers/search_maintenance.py` — новый top-level registrar, подключение в Main принадлежит primary.

Проверки:

- `tests/context_index_separation/test_backend.py` — реальные SQLite scope/rebuild fixtures и alternative backend.
- `tests/context_index_separation/test_maintenance.py` — durable state, ошибки, serialization/crash/retry, cold construction, CLI parity/registration.

Собственные служебные файлы:

- `.pf/logs/context-index-alpha4-maintenance-r3-20261023.md`.
- `.pf/artifacts/context-index-separation-alpha4-20261023/maintenance-r3/` — эта ведомость, change-summary, API handoff, trigger map, stdlib evidence; expected report собирает primary из финального ответа.
- `.pf/tmp/context-index-alpha4-maintenance-r3-20261023/` — retained fixture/check evidence и stdlib runner.

Main, Runtime, original engine, observation owner, immutable assignment/capsule и чужие файлы не изменялись этим worker. Git не использовался; перечень основан на собственных операциях записи.
