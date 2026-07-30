# Граница каталога процессов

Основной каталог содержит только предметно-нейтральные процессы: управление
ресурсами, authoring, инициализацию, context resolution, оркестрацию,
supervision, обновления и универсальное выполнение задач.

Готовые к эксплуатации предметные процессы сохраняют стабильные идентификаторы
и размещаются в официальных пакетах поставки:

- `packs/official/software-development`
- `packs/official/content-workflow`
- `packs/official/verification`

Их manifests содержат `origin: official`,
`bundled_with_distribution: true` и `core_runtime_dependency: false`.
Официальные процессы доступны без копирования из `examples/`, но процессы,
prompts, knowledge packages, capabilities и classifiers попадают в контекст
только после активации pack. Профиль `generic` не активирует предметные пакеты.

Пример может показывать использование официального процесса, но не должен
содержать каноническое определение с тем же process id.

Универсальные runtime-механизмы при этом остаются в `process-forge-core`.
