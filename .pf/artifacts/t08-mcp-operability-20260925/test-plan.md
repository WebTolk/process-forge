# T08 — итоговый план проверки

Область: существующее исправление classifier provenance, доставленное в installed
Core из a180ad624442d4fbe8ac1710073ef7d4c44babc4. Новый source patch не требуется.
Слой source, archive, installed subprocess и реальный host проверяются раздельно.

1. Сравнить fresh/readiness/snapshot/checksum source и installed CLI; сравнить
   process pin и выбранные resources с реальным MCP. Проверить путь нового MCP.
2. На основном проекте проверить sessionless context, восстановленную T08 Work,
   missing_session для Forge-only метода и отказ ресурсу вне snapshot.
3. В изолированном fixture штатно выбрать существующий indexed resource.
   Через host MCP проверить положительные search/resolve, start/state,
   отказ несуществующему evidence, корректные transitions и run_completed.
4. Между двумя стадиями запустить отдельную installed stdio connection;
   требовать continue_existing того же Run/Assignment и уже принятого evidence.
5. В completed fixture внести настоящую manifest drift: поиск должен вернуть
   snapshot_not_fresh. Вернуть исходные bytes без refresh: context снова fresh.
6. Installed regressions: classifier provenance/change sensitivity, JSON-RPC,
   missing_session, bound-session authorization/isolation/search, Garage mode
   with and without session/hooks. Capture stdout/stderr/exit code.
7. Проверить 954 owned hashes, старые evidence/capsule и конфигурацию Workplace;
   оформить review, assurance, local delivery и evolve штатными PF transitions.

Критерий T08: все строки обязательной матрицы PASS. Runtime health warning,
пустой project search grant и unresolved optional registry targets описать явно;
не превращать исправность поддерживаемого MCP в заявление о здоровье всего Workplace.
Координация single_agent; отдельный reviewer/subagent запрещён pinned process.
