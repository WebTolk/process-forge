# План исправления A01–A11

Дата: 2026-09-11. Автор: primary orchestrator. Основание: прямой запрос
пользователя запустить исправления через PF shell workers с контролем качества.
Baseline: 901d0551773fe7a5b382b89ebe95b212b0747e83; VERSION 1.1.0.

## Область и процесс

Исправить все 11 принятых дефектов из аудита, выполнить регрессионные проверки,
независимый review, сохранить исходники и PF handoff для последующей доставки.
Не включать непринятую гипотезу H01. Установка, обновление текущего Runtime,
коммит/push и публикация не входят в эту исходную локальную работу.

Carrier: garage-remediate-audited-a01-a11-defects-with-bounded-junior-pf-shell-wo.
Process: task-batch-execution, единственный предложенный проектом процесс.
PF source CLI подтвердил fresh/ready и создал новый Work. Connected MCP start
отказал из-за уже воспроизведённого A09; далее MCP используется для state и
переходов. Подключённый сервер не перезапускается и не подменяется.
Фиксированных platform/toolchain contracts у проекта нет. Serena symbolic
overview недоступен: Active languages []; используется ограниченный поиск.

## Инварианты и решения до реализации

1. Авторизация ресурса-файла разрешает сам канонический файл, а не всю папку.
   Каталоги сохраняют include/exclude и канонический containment.
2. Expected report разрешается внутри проекта до чтения. Один resolver для
   collector/required output/host authorization, без ослабления hash/provenance.
3. Авторизованный PF-owned report может содержать текст путей после строгой
   проверки identity, attempt, файла, hash и secret scanner. Недоверенный текст
   сохраняет текущие ограничения. Exactly-one и recovery derivation сохраняются.
4. Ошибка одного проекта или host cache не завершает scheduler. Health отражает
   фактическую деградацию и живучесть, а восстановление возвращает готовность.
   KeyboardInterrupt/GeneratorExit и штатное завершение не проглатываются.
5. Живой orphaned owner блокирует singleton takeover; мёртвый owner и concurrent
   старт обрабатываются по существующему протоколу без удаления чужого lock.
6. Источник миграции проверяется в архиве до первого изменения. Ошибка применения
   оставляет структурированное recoverable состояние и сохраняет backup.
7. Session ID — точная opaque identity. Существующие lowercase records должны
   работать; безопасное имя файла не должно объединять разные ID. Старые записи
   читаются по точной metadata identity, collision cases проверяются отдельно.
8. MCP валидирует JSON-RPC до dispatch; notification не создаёт response;
   ошибки parse/envelope/params различаются. Валидные клиенты сохраняются.
9. Classification source label стабилен при переносе distribution. Нельзя просто
   удалить provenance/fingerprint и скрыть истинное изменение classifier.
   Предпочтительно минимальное стабильное имя относительно owning distribution
   для его ресурсов, project-relative имя для локальных ресурсов; совместимость
   действующего source snapshot проверяется отдельно.
10. Разные lifecycle facts не схлопываются по session id. Повтор одной доставки
    должен быть идемпотентен; ограничения provider identity явно фиксируются.

## Владение файлами и очередность

Три shell-воркера одновременно максимум. Модель gpt-5.6-luna, high для сложных
границ; narrow briefs без повторного общего аудита. Каждый пишет только свой
код, собственный smoke и evidence. Регистрация тестов/контрольные суммы — primary
после освобождения tools/processforge.py. Review запускается после реализации.

- Волна 1: A09 (tools/processforge.py), A01 (local_resource_search.py),
  A03/A04/A10 (service.py и собственные smokes).
- Волна 2 после освобождения файлов: A02/A06 (tools/processforge.py + host.py),
  A05 (core_update.py), A08 (mcp_server.py).
- Волна 3: A07 (tools/processforge.py + session_read.py), A11 (codex_hooks.py).
- Assurance: независимые read-only reviewers по группам после реализации;
  primary запускает настоящие regressions, повторяет fault probes и интеграцию.

## Проверка и доставка исходников

Baseline audit proof повторяем по совпадающим SHA-256 и тестам. Каждый новый
smoke должен различать сломанный baseline и исправленный код; нельзя считать
mock вместо реальной ошибки достаточной регрессией. При sandbox PermissionError
воркер сохраняет тест и прекращает обходы окружения; primary выполняет тест.
Используются disposable fixtures, установленный Workplace не изменяется.

После targeted/related smokes: schema/public cleanliness/checksum checks,
релевантные MCP/Runtime/worker integration, итоговый diff и independent review.
Полная source release suite запускается, если изменения и время выполнения
позволяют получить терминальный результат; её сбой/timeout фиксируется отдельно,
а локальная приёмка не выдаётся за archive/extracted/public release qualification.

Все найденные в review пробелы исправляются в этой работе. Оригинальные audit
артефакты, immutable capsules и посторонние dirty PF файлы сохраняются.
