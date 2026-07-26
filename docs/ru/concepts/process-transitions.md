# Process Transitions

Process transitions - это явные маршруты между авторскими процессами. В проекте они хранятся в `.pf/process-routes.yaml`.

Route описывает исходный процесс, целевой процесс, handoff mode, требуемую роль принимающей стороны, входные artifacts, ожидаемые выходные artifacts и правило возврата.

Передача процесса не является простой сменой статуса. ProcessForge создаёт handoff contract и проверяет, что именно передано и куда должен вернуться результат.

Agent Director владеет решениями о transition routes, готовности handoff,
lease coordination и continuations. Process Execution Inspector может
проверять runtime state назначенной task для route, но не выбирает route, не
выдает lease и не финализирует handoff. Worker выполняет назначенную capsule
task.
