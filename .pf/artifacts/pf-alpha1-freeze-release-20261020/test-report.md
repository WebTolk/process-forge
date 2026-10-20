# Проверки замороженного alpha1 source

Source commit: d32200700c48bdbf796728f01209798d40a986c6.
Чистая detached Git-копия, version 1.3.0-alpha1; посторонний OOP54–55 не включён.

- `python <shared-python-qa>/qa.py --project-root . test -- tests/update_versions/test_selection.py -q`: exit0, 17 PASS.
- `python -B -X utf8 bin/pf.py release-test --root . --public --fail-fast --timeout-scale 1 --trace-smokes`: exit0, 274/274 PASS, без предупреждений. Схемы, checksum inventory, public cleanliness, source smokes, doctor-project, canonical release package и git diff --check прошли.
- `python -B -X utf8 bin/pf.py dev-test --root . --suite supervisor-stress --fail-fast --timeout-scale 1`: exit0, все сценарии PASS.

Точные elapsed/command/commit и итоговые статусы — source-gates.json. Полные
приватные stdout/stderr и native release trace сохраняются в собственном .pf/tmp.
Один итоговый архив уже построен canonical release package step; он будет
скопирован побайтно для публикации, повторной сборки не требуется.

Границы: Windows source qualification; текущая проверка не утверждает POSIX
исполнение, установку на устройство или приёмку alpha настоящим connected MCP.
ZIP content inspection/release-archive-test не выполнялись по прямому указанию
пользователя; проверяются hashes непрозрачных опубликованных файлов.
