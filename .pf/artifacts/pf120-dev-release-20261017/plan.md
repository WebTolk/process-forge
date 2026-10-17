# Dev-кандидат 1.2.0: план предрелизной проверки

2026-10-17, primary / release-engineer. Источник: 280e00d9520e8aff7ac49f8173a940cf130b9ff4. Доставку исходников необходимо подтвердить чтением обеих dev-веток: первые push остановились на DNS; исходный коммит сохранён и повторно не создаётся.

Текущая Work создана отдельно после terminal Work проекции. Context fresh, Forge; immutable capsule 9b9b49dd8a156c764ef7517f8f96b5b3f164ae9ce3216cc94c3489c0beff46df, valid/ready. Разрешены только чтение и собственные артефакты/временные материалы. Изменения продукта потребуют отдельной ограниченной Work. Один primary; subagent_policy.allow=false. Лог: progress.md. Использованы проектные инструкции, release/update/runtime CLI и локальные docs.python-devguide/testing, docs.python-packaging/distributing-modules.

Пользователь явно поручил новый dev-релиз, установку, перезапуск PF app-server и полную проверку. Это отдельное разрешение на штатные административные операции; файловая капсула сама его не предоставляет. Старый успешный apply не повторяется. Приватные настройки, история, unrelated dirty state и immutable capsules сохраняются.

1. Подготовить чистый detached Git worktree с LF на точном source commit; проверить native checksum/release gates и собрать новый именованный dev ZIP/sidecar. Версия Core остаётся 1.2.0; dev-кандидат различается commit/hash, стабильный update feed/tag не публикуется.
2. Выполнить полный public release-test исходников и полный consumer release-archive-test нового ZIP. Сохранить итоги по каждому контролю, исключения и границы среды; прежние 274 проверки не заменяют новое выполнение. Не нагружать процессор параллельными сериями замеров.
3. Снять текущие install/Runtime/MCP identity, native core-update status/plan, активные worker/request состояния и конфигурацию logging. Сохранить checkpoint. Штатно остановить app-server, применить новый архив ровно один раз и запустить сервер прежним владельцем. Не использовать force для обхода занятости.
4. Проверить installed manifest/bytes/version, doctor-workplace, CLI surfaces, Runtime auth/protocol/ready/scheduler и устойчивость. Сырые хуки должны остаться выключены, events включены.
5. Проверить MCP через установленную поставку, затем фактически подключённый MCP отдельно: source provenance, fresh pf.context, точная Work, поиск/resolve. Независимый stdio не является доказательством переподключения действующего хоста. Операции, требующие управления жизненным циклом внешнего хоста, не подменяются новым PID Runtime.
6. Сопоставить матрицу функций: CLI, MCP, Work/continuation/capsules, resources/search, Runtime/monitor, hooks/events/chat, Agent Ledger/worker lifecycle, journals/SQLite/recovery, config/updates/packs/authoring. Сочетать полный изолированный suite с безопасными live-проверками существующего устройства.
7. Провести primary review после выполнения, закрыть native стадии и doctors, сохранить report/handoff, отдельный scoped commit, параллельные push и полные SHA readback.

Риски: source/archive/installed/Runtime/MCP имеют разные времена жизни. Неизвестные metrics не равны нулю. Холодный parse-cache не означает холодный диск; измерения Windows не квалифицируют Linux/macOS. Пользовательская переписка и live hooks не должны становиться тестовыми данными; изменяющие сценарии выполняются в изоляции.
