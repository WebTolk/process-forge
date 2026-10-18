# Handoff: Core checks

Independent source review accepted all nineteen final product hashes; exact dual-remote delivery and native closeout follow.
Точные run/assignment/context находятся в native start receipt и immutable
капсуле. Использовать только эти selectors; после run_completed не возобновлять
terminal Work и не выбирать историческое назначение по умолчанию.

19 продуктовых файлов, 18 перенесённых алгоритмов и 19 удалённых определений
зафиксированы в primary/product-manifest.json и verification.json. Сравнение
242/242, 43 исключения, 18 annotation maps, десять существующих smoke PASS.
Один тест справки повторён после исправления ссылки, прочие прогоны сохранены.
Symlink-пробы недоступны; упаковочные и ZIP-content проверки исключены.

После ревью коммитить только выбранные пути, push того же полного SHA в origin/dev
и gitverse/dev, проверить обе ветки. Для GitVerse только GITVERSE_TOKEN,
credential helper отключён; не записывать секреты. Завершить все шесть native Work,
выполнить root run-doctor и перечитать исходную архитектуру перед новым scope.
Сохранить посторонние dirty/index изменения. Источником фактической поставки
будет primary/delivery/core-checks.json.

Source-only не квалифицирует архив, install, Runtime и connected host.
Инфраструктура и новые MCP-ресурсы вне этой задачи. Пользователь разрешил
автономный цикл до 2026-10-19 09:00 по устройству с завершением текущих задач
и итоговым ночным отчётом.
