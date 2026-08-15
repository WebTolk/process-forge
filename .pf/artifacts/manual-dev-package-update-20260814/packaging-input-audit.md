# packaging-update-input-audit

## 1) Нужные входные версии для пакета

- Версия дистрибутивного release hardcoded в CLI и **не передаётся флагом**:
  - `PROCESSFORGE_VERSION = "1.0.2"`
  - `RELEASE_ARCHIVE_VERSION = "1.0.2"`
  (в `tools/processforge.py`)
- Следовательно, команда `release-pack` всегда пишет манифест с версией `1.0.2`, пока эти константы не изменены в коде.
- В `updates/processforge-update-index.yaml` текущая база версий дистрибутива также указывает `current_version: "1.0.2"` и `channels.stable.latest: "1.0.2"`.

## 2) Команда упаковки (release-package command)

- Базовый вызов:
  - `python bin/pf.py release-pack --root . --output dist/processforge.zip`
- Опции:
  - `--output` — обязательный путь итогового архива.
  - `--dry-run` — только печать содержимого без записи.
- Поведение `release-pack`:
  - требует clean git source для provenance (`commit`, `tree`, `SOURCE_DATE_EPOCH` для детерминизма).
  - использует `RELEASE_ARCHIVE_VERSION` как `version` в release-манифесте.
- Поэтому поставить «текущий коммит как `1.1.0-dev`» через этот механизм нельзя без изменения версии в коде/входных данных перед сборкой.

## 3) Что нужно для manual staging update-кандидата (1.1.0-dev)

### 3.1 Что надо в `update_sites`
Для любого installable-субъекта в его manifest должно быть (минимально):
- `manifest_url`
- `changelog_url`
- `channel`
- `trust`/`policy` (включая разрешение `allow_stage` / `allow_apply` для ручного процесса)

### 3.2 Формат манифеста кандидата, который читает `update candidates refresh`
Обязательные поля после нормализации кандидата (по схеме и коду):
- `subject.type`
- `subject.id`
- `subject.scope`
- `available_version`
- `source_id`
- `status` (должен стать `available` для `stage`)
- `installable` (должен быть `true`)
- `download_url`/`sha256` (или `artifact_sha256`) на архив
- `changelog_url` (необязательно для применения, но используется для показа changelog)

### 3.3 Что важно для верификации/применения
- `update stage --candidate`:
  - требует найденный candidate, `status == available` и `installable == true`.
  - копирует артефакт в `runtime/update/staged/<candidate-id>/`.
  - пишет staged record с `sha256`.
- `update verify --candidate`:
  - проверяет `sha256` staged artifact.
  - для `.zip` дополнительно сверяет `id/type/version` внутри `package.yaml` артефакта с `candidate.subject.id/type` и `candidate.available_version`.
- `update apply --candidate --confirm`:
  - требует только предварительно staged+verified кандидат и подтверждение `--confirm`.

## 4) Непосредственно для `knowledge-package-release` (если candidate создаётся через пакетный релиз)

- Команда:
  - `python bin/pf.py knowledge-package-release --hub <hub> --package <id> --version <версия> --output <zip>`
- В сгенерированном локальном update-манифесте для версии ставится:
  - `channels.stable.latest = <версия>`
  - `channels.stable.versions[].version = <версия>`
  - `download_url`, `sha256`, `changelog_url`
  - `update_policy.install_path = packages/<package-id>`
  - и обновляется `package.yaml` с `package.update_sites` (включая `manifest_url`, `allow_stage`, `allow_apply`, `install_path`).
