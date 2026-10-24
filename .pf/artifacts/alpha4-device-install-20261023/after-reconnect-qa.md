# Alpha4 post-reconnect assurance

Нового production Python нет. Все1497 installed payload hashes повторно
совпали с опубликованной alpha4; это те же байты, для которых уже сохранены
installed-pytest.json, installed-native-smokes.json, code-quality-report.json
и acceptance-provenance.json. Повтор всей неизменённой suite не требуется.

Проверены actual MCP process provenance после native apply, hook online,
fresh context и exact valid/ready Work, native verified search/resolve, native
installed status/version и CLI project-context-check на том же snapshot.
Успешные последовательные вызовы не удаляют первые timeout receipts.

Review нового product code не применим: installation-only Work использует
ранее квалифицированный source/archive и не меняет код. Нельзя считать этот
результат приёмкой alpha5 или утверждать исправление known1.2.0 literal в alpha4.
Два старых global derived-project coverage gaps и прежние warnings/skips
сохранены как ограничения. Core apply/restart не повторялись.
