# T08 — architecture / implementation plan / decision log

## Решение

Доставить уже существующее исправление c810381 из чистого HEAD a180ad6. Не добавлять новый продуктовый патч. Выбор согласован с PF vision: исправление общего provenance в ядре, перезапуск — lifecycle конкретного host adapter, не новая зависимость ядра от Codex.

## Выполнение

1. Изолированный detached Git candidate в .pf/tmp/t08-core-candidate-20260925. Не включать dirty основной checkout, текущие приватные артефакты или настройки в пакет.
2. Выполнить ограниченный source regression набор и штатный release-pack; проверить архив, manifest parity и extracted quick. Это тестовая поставка, не новая публичная квалификация релиза.
3. core-update plan against installed Core, проверить added/changed/removed, collisions/local modifications/migrations. При конфликте не применять force автоматически.
4. Перед apply сохранить read-only Runtime status/doctor и backup состояния установки. Остановить только PF Runtime этого Workplace штатной командой, если он работает. Current MCP не убивать, инструменты старого MCP после apply не считать acceptance.
5. Apply штатным core updater из независимого кандидата. Retain backup dir/control manifests/journal. Если apply падает — core-update status/repair, не повторять слепо. Recovery по exact journal: вернуть изменённые/удалённые owned bytes из files, убрать только добавленные этим update пути при совпадении нового hash, вернуть old manifest последним. Никакой массовой чистки или автоматического rollback незавершённого Workplace migration.
6. Проверить installed hashes, fresh context без refresh/обходов, targeted MCP subprocess tests и Workplace doctor. Восстановить optional Runtime штатным start с прежней Workplace конфигурацией; новые task scheduler hooks не создавать.
7. Создать подробный handoff с точной Work/stage, candidate/archive/backup/log paths, командами, PASS/FAIL и remaining gates. Только после этого попросить оператора restart сессии.
8. В новой сессии подключённым MCP: context/search/resolve positive + denied checks, изолированный Work lifecycle, reconnect continuation; отличать настоящую host acceptance от изолированного stdio теста. Завершить T08 через PF, затем начать T01 отдельной Work.

## Границы

Никаких публичных релизов, push, изменений чужих проектов, broad process kills, вмешательства в host config или одноразовой hot-memory подмены. T09 PSR-like diagnostics и T10 branding выполняются позже. Архив/кандидат временно удерживаются для проверки и отката; после закрытия T08 оставить durable результаты и очистить только exact T08 scratch.
