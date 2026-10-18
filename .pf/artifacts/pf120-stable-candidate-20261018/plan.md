# План подготовки стабильной поставки 1.2.0

Дата: 2026-10-18T03:45:33.460Z. Primary / release-engineer. Пользователь поручил продолжить предрелизную работу; GitVerse обслуживается через токен без его вывода.

Результат этой Work: проверенный канонический архив 1.2.0, sidecar с точным commit/tree/SHA256, проект stable metadata и release notes, подтверждённые release gates и конкретный план публикации. Действующий stable channel, публичные теги/assets, продукт и установленная среда этой Work не изменяются.

Точная новая Work связана с завершённой dev-приёмкой через native predecessor/handoff. Context fresh; capsule388a24a0ec8d084e4cffcbbe5b5ac269214e68f59f0881f91e2c5b1c728c6d6e valid/ready. Разрешены собственные artifacts/scratch/handoff, продуктовые записи запрещены. Subagents запрещены капсулой. Платформа/toolchain overlay не выбраны; используем проектные native CLI/release contracts и разрешённые локальные Python docs.

1. Сверить checklist/publishing policy, VERSION/CHANGELOG/docs, стабильный feed/schema, предыдущие завершённые systems/dev acceptance и удалённые refs. Не дублировать terminal Work и не применять auto-selected legacy backlog.
2. Зафиксировать точный clean source commit, создать detached LF worktree в собственном scratch. Native schema, cleanliness, checksum и release-check; полный source release-test --public и требуемый supervisor-stress.
3. Native release-pack канонического processforge-1.2.0.zip/sidecar с этого же commit. Сверить состав, source tree, manifest, ZIP hash и весь payload с принятым dev-кандидатом.
4. Native release-archive-test full без выборочного исключения проверок. Таймауты выбрать по прошлым измеренным полным прогонам; source и consumer выполнять последовательно.
5. Подготовить proposed stable channel document с действительными URL будущих assets и фактическим SHA, release notes, migration guidance и проверяемую последовательность promotion. Схемы проверить штатно; staged metadata не считать уже опубликованным feed. Исторический специально переизданный1.1.0 не превращать в новый blocker.
6. Primary review после реализации; итоговый report с матрицей gates, ограничениями и готовыми артефактами. Native lifecycle/doctors, privacy scan, отдельный scoped evidence commit, parallel push/readback обоих dev remotes.

Граница публикации: maintainer contract требует tag на точном source commit, immutable release assets и лишь затем исторический sidecar/изменение stable channel, после чего проверка discovery предыдущей установленной версии. Подготовить все конкретные материалы до передачи этой операции; никаких повторных install/server/MCP restart или refresh свежего контекста.

Риски: полный source и consumer suites занимают десятки минут; их частичный успех не равен PASS. Текущий canonical archive может отличаться от принятого dev ZIP только generated provenance — это нужно доказать. Старые hashes1.1.0 не подменяют actual1.2.0. Неизвестные metrics/непроверенные платформы сохраняют свои границы.
