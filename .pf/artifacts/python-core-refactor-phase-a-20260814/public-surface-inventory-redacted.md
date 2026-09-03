# Public-surface inventory (redacted)

## Что подтверждено (только по фактам из разрешённых источников)

### CLI-поверхность
- `bin/pf.py` является точкой запуска: `main` делегирует вызов в `tools/processforge.py` через `exec_processforge` (`bin/pf.py:main`, `bin/pf.py:exec_processforge`).
- Команды релизного контура объявлены в CLI parser’е `tools/processforge.py`:
  - `release-check`, `release-test`, `release-pack`, `release-archive-test`, `clean`, `examples-check` (`tools/processforge.py:24599-24663`).
- Опция `--public` есть у `release-test`/`smoke-all` и влияет на включение публичных гейтов (`tools/processforge.py:24604`, `tools/processforge.py:24617`).
- Список smoke/проверок для release-test задаётся явно в `release_test_commands(...)`, без автодискавери по шаблону `smoke_*.py` внутри самой функции сборки команд (`tools/processforge.py:6549-6697`).

### Release-пакетирование и `releaseignore`
- Набор файлов, из которых формируется релиз, задаётся константами:
  - `RELEASE_ROOT_FILES` (`tools/processforge.py:5963`),
  - `RELEASE_PF_PUBLIC_FILES` (`tools/processforge.py:5964`),
  - `RELEASE_DIRS` (`tools/processforge.py:5962`).
- Обязательные пути для релизной валидации перечислены в `RELEASE_REQUIRED_PATHS` (`tools/processforge.py:5965-5983`), включая:
  - `README.md`, `README.ru.md`, `QUICKSTART.md`, `QUICKSTART.ru.md`, `requirements.txt`, `.processforge-releaseignore`, `.pf/AGENTS.md`, `.pf/process-forge.yaml`, `.pf/hooks.yaml`, `checksums/processforge.sha256`, `bin/pf.py`, `VERSION` и др.
- Паттерны исключения загрузки в архив берутся из `.processforge-releaseignore` в `release_ignore_patterns(...)` (`tools/processforge.py:6024-6033`).
- `release_pack` применяет эти правила: исключает совпадения с `release_ignore_match(...)` и `release_path_is_forbidden(...)` при формировании `files` (`tools/processforge.py:7056`).
- Проверка сборки/валидации:
  - `release_checks()` фиксирует фейл при пустом/отсутствующем `.processforge-releaseignore` (`tools/processforge.py:6232-6243`),
  - `command_release_pack()` требует отсутствие `FAIL` из `release_checks()` (`tools/processforge.py:7056-7061`),
  - `command_release_archive_test()` проверяет целостность архива и, при `--root`, актуальность манифеста (`tools/processforge.py:7296-7303`, `tools/processforge.py:7267-7277`).
- В `.processforge-releaseignore` действительно перечислены исключаемые пути:
  - `.pf/runtime/`, `.pf/artifacts/`, `.pf/reviews/`, `.pf/handoffs/`, `.pf/runs/`, `.pf/contexts/`, `.pf/assignments/`, `.pf/dogfooding/`, `.pf/private-notes/`, `.pf/cache/`, `tools/__pycache__/`, `__pycache__/`, `*.pyc`, `*.pyo`, `.serena/` и др. (`.processforge-releaseignore`).

### Смоуки/проверки, которые публикуются как часть публичного релизного контура
- Чек‑лист для релиза перечисляет публично-релизные шаги и команды явно (`docs/release-checklist.md`).
- В коде список release-команд и их вложенные smoke совпадает с принципом явного перечисления в `release_test_commands(...)`; публичный запуск делает фильтрацию по `public_gate`, а не глобальный discovery (`tools/processforge.py:6549-6702`).

### Удалены неподтверждённые формулировки
- Убраны формулировки о «поиске `smoke_*.py`» или «неподтверждённой автодискавери» — такие утверждения не опираются на единый явный источник в проверенных файлах.
- Убраны непроверяемые/расплывчатые описания `releaseignore` с предполагаемым расширенным охватом; замена сделана на прямые ссылки на `release_ignore_patterns`, `RELEASE_*` и фактическое содержимое `.processforge-releaseignore`.

## Текущее состояние публичных утверждений по упаковке
- Единственный источник для упаковки и публичного скоупа в коде: `tools/processforge.py` + `docs/release-checklist.md` + `.processforge-releaseignore`.
- Версия и зависимости проекта:
  - `VERSION: 1.0.2` (`VERSION`),
  - `requirements.txt: PyYAML>=6.0` (`requirements.txt`).