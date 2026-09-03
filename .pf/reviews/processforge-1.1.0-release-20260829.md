# Отчёт независимой ревью проверки релиза `1.1.0`

## 1) Итоговая оценка

`1.1.0` в целом выглядит пригодным к публикации по артефактному стеку (ZIP, sidecar, checksum, тесты), но есть процедурные отклонения в текущем окружении и несогласованность в одном из отчётов (см. [release-surface-audit](D:/Dev/process-forge/.pf/artifacts/processforge-1-1-0-release-20260829/release-surface-audit.md)).

## 2) Ключевые находки (по важности)

### 2.1 Средняя — Непоследовательность в отчёте `release-surface-audit`
- В [release-surface-audit](D:/Dev/process-forge/.pf/artifacts/processforge-1-1-0-release-20260829/release-surface-audit.md) заявлены блокеры: `README.md` со значком `version-1.0.2` и нечистый git для `release-pack`.
- Проверка по факту релиза показывает, что в пакете [`dist/processforge-1.1.0.zip`](D:/Dev/process-forge/dist/processforge-1.1.0.zip) `README.md` содержит `version-1.1.0` (также проверено в source [`README.md`](D:/Dev/process-forge/README.md)).
- [Release-сборка](D:/Dev/process-forge/.pf/artifacts/processforge-1-1-0-release-20260829/release-build-report.md) показывает `source dirty` для sidecar = `false` и `candidate Git status ... clean detached HEAD`, т.е. блокирующие факты относятся к текущему окружению/истории отчёта, а не к опубликованному candidate.
- Риск: сниженная точность `release-surface-audit` снижает надёжность автоматического приёмочного сигнала без дополнительной верификации.

### 2.2 Низкая — Процедурные артефакты релиза не доведены до финального состояния
- В [release-build-report](D:/Dev/process-forge/.pf/artifacts/processforge-1-1-0-release-20260829/release-build-report.md) указано, что:
  - не создавались tag и GitHub release;
  - release worktree сохранён до завершения независимого review.
- Это не нарушает корректность самого ZIP, но нарушает “release hygiene” как процессную завершённость и может осложнить последующую воспроизводимость/аудит.

## 3) Что проверено как соответствующее

- sidecar manifest корректный и согласован: `dist/processforge-1.1.0.manifest.json` указывает `version=1.1.0`, `entries=898`, `sha256=1530...` и commit `8f291...` с `dirty=false`.
- Архивные ворота пройдены:
  - `release-check`/`release-test --public` — PASS;
  - parity manifest↔zip PASS;
  - extracted archive help и `release-archive-test --extracted-test full` — PASS.
- Политика обновления и миграция:
  - [updates/processforge-update-index.yaml](D:/Dev/process-forge/updates/processforge-update-index.yaml) содержит `current_version: "1.1.0"` и запись `1.1.0` без обязательной миграции.
  - Документация update-системы описывает единственный управляемый переход `1.0.2 -> 1.1.0` с staged-updater flow ([docs/getting-started/update-system.md](D:/Dev/process-forge/docs/getting-started/update-system.md), [docs/ru/getting-started/update-system.md](D:/Dev/process-forge/docs/ru/getting-started/update-system.md)).
- [release-build-report](D:/Dev/process-forge/.pf/artifacts/processforge-1-1-0-release-20260829/release-build-report.md) содержит выполненный proof transition с 1.0.2: apply с `--confirm` успешен, `post_update` статус `installed`, `incomplete update=false`, ключевые проверки после обновления PASS.

## 4) Рекомендуемое решение

1. Перегенерировать/переоценить `release-surface-audit` на чистом состоянии и убедиться, что в нём не остаются исторические ложные блокеры.
2. Принимать артефакт релиза по итогам отдельной final-квалификации только после установки tag/GitHub release и зафиксированного процесса публикации.