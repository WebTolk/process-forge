# Отчёт: аудит поверхности релиза `1.1.0`

## 1) Итог

**Статус: неготов к публикации без фиксов (блокеры есть).**

## 2) Найденные несоответствия (по убыванию важности)

### Блокеры

1. **Несогласованность версии в публичной документации**
- `VERSION`: `1.1.0`
- `tools/processforge.py`:
  - `PROCESSFORGE_VERSION = "1.1.0"`
  - `RELEASE_ARCHIVE_VERSION = "1.1.0"`
- `updates/processforge-update-index.yaml`: `current_version: "1.1.0"`, запись `1.1.0`
- `README.md` показывает значок версии `version-1.0.2` (уже неактуально для релиза `1.1.0`).

2. **Требование "чистого" git для `release-pack` нарушено в текущем состоянии репозитория**
- `release_pack` вызывает `release_git_provenance`, которая требует clean git с исключением только:
  - `.pf/artifacts/projections/command-history.md`
  - `.pf/artifacts/projections/stage-obligations.json`
- Текущий `git status --porcelain` содержит множество `M` и `??` по `.pf/`, `docs/`, `tools/`, `src/`, т.е. ожидаемый релизный preflight для `release-pack` будет падать.

### Риски (не блокируют немедленно, но требуют проверки/проведения)

3. **Публичная документация релиза может быть не полностью синхронизирована со структурой контроля**
- `docs/release-checklist.md` актуален и включает расширенную цепочку проверки, включая:
  - `python -m py_compile ...`
  - `release-check`
  - `release-test --public --fail-fast`
  - `release-pack --output dist/processforge.zip`
  - `release-archive-test --extracted-test full`
- Однако из-за блокера в п.2 release pipeline не пройдёт до этой стадии без очистки дерева.

## 3) Валидация поверхности пакета и входов (1.1.0)

- **Объект релиза**: `PROCESSFORGE_VERSION`, `RELEASE_ARCHIVE_VERSION`, `RELEASE_NAME`, и `changeset` в `updates/processforge-update-index.yaml` согласованы на `1.1.0`.
- **Migration-маршрут**:
  - `updates/processforge-update-index.yaml` содержит `version: "1.1.0"` с `migration.required: false`.
  - Текст migration-файла `updates/migrations/1.1.0-prerelease-hardening.md`:
    - «No mandatory project migration required».
    - Рекомендуются команды `project-context-refresh`, `search-index tick`, `doctor-project`.
- **Фактический релизный пакетный контроллер (из `tools/processforge.py`)** требует:
  - обязательные пути из `RELEASE_REQUIRED_PATHS` (в т.ч. `checksums/processforge.sha256`, бинарники `bin/*`, `src/processforge_core`, `tools`, `schemas`, `templates`, `processes`, `packs`, `prompts`, `docs`, `examples`, `policies`, `seeds`);
  - наличие и непустой `.processforge-releaseignore`;
  - отсутствие запрещённых директорий/файлов в источнике (`.git`, `.idea`, `.pf/runtime`, `.pf/artifacts`, `.pf/runs`, `.pf/context...`, `.vscode`, `*.ps1`, архивы, `.env`, локальные конфиги и т.п.).

## 4) Наиболее вероятные потенциальные блокеры в текущем окружении для публикации `1.1.0`

- `release-pack`:
  - чистота git (см. п.2);
  - preflight `validate-process-forge-checksums.py --check` и `validate-public-cleanliness.py`;
  - валидность публичных текстов (локальные пути/секреты/PS1/`forbidden`-паттерны).
- `release-test --public`:
  - обязательные проверки + `git diff --check`.
- `release-archive-test`:
  - потребует успешного тестирования распакованного архива.

## 5) Короткий список действий до публикации

- Обновить `README.md` значок версии с `1.0.2` на `1.1.0`.
- Очистить git workspace для релизной ветки до чистого состояния (разрешив только разрешённые служебные проектные `.pf/artifacts/projections/*` при крайней необходимости).
- После очистки запустить:
  - `python tools/processforge.py release-check --root .`
  - `python tools/processforge.py release-test --root . --public --fail-fast`
  - `python tools/processforge.py release-pack --root . --output dist/processforge.zip`
  - `python tools/processforge.py release-archive-test --archive dist/processforge.zip --root . --extracted-test full`
