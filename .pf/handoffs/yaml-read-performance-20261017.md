# Handoff: primary -> operator

Objective: исправить повторный разбор растущих YAML в PF, проверить общую точку чтения и доставить исправление на устройство с фактическим замером CPU.

Current status: исходный код, архив, установленный Core и фактический Runtime проверены. Завершается точная Work `garage-yaml-read-performance-20261017-fix-the-measured-repeated-growing`, assignment `yaml-read-performance-20261017-fix-the-measured-repeated-growing-yaml-pa`, context `yaml-read-performance-20261017-fix-the-measured-repeated-growing-yaml-pa-capsule`, checksum `sha256:ae0e5ec515d7e3364d71e6a69b8645fb0cdeeaebc87d20aee8ffcb315dc91c20`. После terminal closeout её не возобновлять.

Input artifacts: `.pf/artifacts/yaml-read-performance-20261017/report.md`, неизменяемые stage evidence, delivery-report.md, installed-byte-proof.json, cpu-comparison.json и profile-summary.json. Исходный коммит `8f00ca1711f1d7ad276da61a9fcbec907da0cd36` присутствует в обеих ветках dev. Собственные записи завершения публикуются отдельным коммитом без изменения установленного кода.

Files changed: общий ограниченный YAML parse cache, request scope/document reader, поиск Run, Runtime metrics, точечные проверки, EN/RU документация и checksum inventory; полный список — source-commit.json. Сохранены чужие изменения и локальные конфигурации.

Files not to touch: неизменяемая капсула, закрытые Work, чужое состояние `.pf`, ранее мигрированные журналы и их резервные копии. Архив `.pf/tmp/yaml-read-performance-20261017/processforge-1.2.0-dev-20261017-yaml-8f00ca1.zip`, SHA256 `54093affb5cfd9905f5eec335475cb5abba2de359bfe717a359eab94a4694223`, уже установлен обновлением `core-update-20261017T074204Z`; повторять apply или миграцию SQLite не требуется.

Known issues: минутный CPU уменьшился с18,587% до15,4427% общей мощности4 логических процессоров. YAML больше не встретился в нативных parser-стеках выборки; Run discovery3,44% вместо49,55%. Оставшийся Host JSON37,8МБ занимает76,56% GIL-выборок чтения/записи. Это отдельное следующее исследование, не устранённый дефект текущего патча. Остаются прежние degraded/scheduler и закрытый фактически подключённый MCP. Общая приёмка1.2.0 отложена.

Required checks:14 применимых smoke-программ и исходные/архивные проверки пройдены; необязательный исторический fixture явно пропущен. Установленные1302 файла сверены,5 состояний конфигурации сохранены. Runtime PID18280, instance `e6906e3fd2a74ffdba75b60cae8df1b7`, start `2026-10-17T07:42:08Z`, ready/degraded. При продолжении сверять фактическую идентичность; CLI context свежий, MCP Transport closed. Итоговое terminal-state/run-doctor доказательство находится в том же каталоге артефактов после завершения.

Next recommended action: при отдельном поручении начать новую ограниченную Work по Host JSON, прочитав текущий контекст и фактические владельцы данных. Пользователь подтвердил кэш в ОЗУ; это не отдельный сервис, файлы кэша в проектах не создаются. Лимит64МиБ оценочный на процесс, очистка LRU/завершением процесса; чтение текущих YAML и проверка прав сохраняются.
