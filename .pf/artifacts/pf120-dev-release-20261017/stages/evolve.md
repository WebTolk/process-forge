# Evolve: итог dev-приёмки 1.2.0

Status: ready. Primary / release-engineer, 2026-10-17T20:39:29.864Z.

Result boundary: source8ea152b / final ZIP e332a74d принят на текущем устройстве по согласованным source/archive/installed/Runtime/actual connected MCP слоям. Историческая source fixture failure закрыта точной test-only правкой и полным финальным consumer suite; эта история сохраняется. Product/infrastructure/config/history не менялись в продолжении после reconnect.

Lessons and proposals:

1. Разделять independent installed stdio и actual host. Сохранять точный native continuation, apply checkpoint и manifest/metadata SHA; после переподключения проверять owner/root/start, fresh context, exact Work и разрешённый ресурс. Одноразовый apply и перезапуск server не повторять для получения другого слоя доказательств.
2. В замерах host context явно указывать инструмент целиком, warm-up и отдельные samples; сравнивать полные ответы. Здесь все шесть равны, медиана пяти2.021s. Исторический одиночный slow call не превращать в controlled A/B.
3. Bounded shutdown observer на большой истории может давать partial. Будущее изменение требует отдельной ограниченной Work с воспроизводимой большой историей, сохранением fail-closed поведения и различением unknown/zero. В текущей delivery только зафиксировано существующее ограничение; defaults/guard не менялись.
4. Для будущих release notes сохранять отдельные сведения об optional/platform gaps и partial metrics. Не выдавать успешный wrapper за квалификацию Linux/macOS, всей матрицы Python или нового реального worker.

Instruction/knowledge/rule changes: not_applicable in this evidence-only scope; proposals retained in this report, no approved instructions or knowledge package modified. Existing project conventions already cover exact continuation, immutable context and provenance layers. Отдельная comprehensive installed-systems task ранее зарегистрирована; дублировать её этим closeout не требуется.

Follow-up: native task/run/continuation doctors, own public-evidence privacy scan, scoped commit and parallel push/readback both dev branches. Public stable release — отдельная точная поставка с её archive/hash/metadata и release gates. Эта terminal Work после закрытия не возобновляется.
