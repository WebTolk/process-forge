# План общей проверки 1.2.0
2026-10-17, primary. Рабочий контекст valid/ready, checksum 8d98963440a33b3c50761ea1a01b6f8c31f4f13740fd8b04e5762690176894c0. Разрешены чтение и собственные артефакты. Сервисы не запускаются и не перезапускаются.

Сначала закрыта прежняя Work устройства: actual MCP PID18576 после последней доставки, точная Work и resource resolve проверены; native run/task doctor PASS. Старый backlog pf120-installed-systems-check-20261016 имеет legacy_unpinned/legacy_contract_incomplete и пустой stage. Поэтому для его единственного выполнения создан текущий bounded governed Work, а исходная запись будет закрыта ссылкой на его результат; дублирующий аудит не запускается.

План:
1. Сопоставить точный latest product commit, archive manifest/sidecar, текущую установку и Runtime/MCP identity.
2. Построить матрицу подсистем по immutable receipts полного274/274, focused archive/installed tests и текущих live вызовов.
3. Измерить CLI холодные процессы и MCP в последовательных повторах; сохранить individual samples, медиану и диапазон. Work admission измерено один раз при создании текущей Work и не повторяется ради статистики.
4. Снять три30-секундных последовательных quiet CPU/память окна без PF-команд в них, runtime status до/после. Quiet означает отсутствие PF workers и foreground PF-команд; фоновые scheduler/hooks продолжают обычную работу.
5. Выполнить лишь проверки, закрывающие сегодняшние пробелы. Полный274-набор не повторяется при неизменных продуктовых байтах.
6. Проверить EN/RU release/migration docs и checksum/public gates, подготовить точный список оставшихся действий и кандидат к публикации.
7. Review результатов/ограничений, native lifecycle/doctors, отдельный коммит собственных безопасных материалов и readback двух dev remotes.

Распределение: один primary, subagent_policy.allow=false; отдельных исполнителей не создаём. Независимые code reviews/qualification используются из уже завершённых исправлений; текущий отчёт проверяет primary и указывает границу независимости.
Логирование: progress.md; stage evidence фиксируются отдельно и после использования не меняются.
Риски: source/archive/installed/Runtime/MCP различаются по времени и приватной конфигурации; metrics partial нельзя выдавать за нули; Windows данные не подтверждают Linux/macOS. VERSION1.2.0 не означает соответствие latest source старому ce1c51d.
