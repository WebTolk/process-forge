# Архитектура и план исправления LF/CRLF context parity

## architecture
Owner политики: существующий ProjectSnapshotSourceCheckService.compare.
Owner live-файлов/fingerprints: существующий ProjectSnapshotSourcesReader, выбирающий активные файлы через OfficialProcessPackReader.
FileDigestReader остаётся прежней общей raw-byte инфраструктурой; используется его sha256_bytes для ограниченных альтернатив представления.

SnapshotSourcesReader получает общий внутренний обход official pack sources (path/id/display), использующий прежние active_records и порядок manifest/classifiers.
Общий helper разрешает raw local workplace manifest точно прежним способом; повторный probe использует тот же источник, а не guessed distribution paths.
Новый метод official_pack_checksum_variants(source_ids) читает только нужные live official files и возвращает для id три digest: raw, равномерный LF, равномерный CRLF. Он не меняет read()/fingerprint() output.
SourceCheckService при несовпадении official raw checksum принимает альтернативу лишь когда повторно прочитанный raw digest совпал с текущим fingerprint и recorded checksum совпал с одним из трёх представлений.
Probe выполняется только при official mismatch, один раз за операцию. Никакого межоперационного кэша.
Остальной порядок added/changed/removed, package-* skip и error strings остаётся существующим.
CLI/MCP/Host consumers уже используют этот owner; транспортные изменения не планируются.

## decision-log
Принято локальное доказательство равенства LF/CRLF без mutation snapshot и без нового публичного поля.
Отклонены: принудительный refresh/restart как исправление; отключение source-check; нормализация общего FileDigestReader; YAML semantic equality; app-lifetime cache; ручное изменение установленного pack для совпадения hash.
Изменение правил является явным bug fix, а не механическим OOP переносом.
Mixed-ending legacy snapshot, который невозможно доказать как один из uniform вариантов, остаётся консервативно stale. Одиночный CR не нормализуется.
Обновление установленного Core и reload здесь не разрешены; при необходимости подготовить concrete reviewed delivery и запросить отдельное решение оператора.

## implementation-plan
1. Добавить meaningful pytest regression для source/installed-style LF/CRLF на прежних raw snapshots; сначала зафиксировать отказ.
2. Добавить общий source helper и read-only checksum-variant probe в snapshot_sources.py; применить правило в source_check.py.
3. Проверить оба направления LF/CRLF, genuine content drift, raw project/workplace strictness, source add/remove, no-workplace and inactive pack, live same-size/mtime drift и отсутствие кэша.
4. Проверить core-only import без CLI/transport и неизменность raw fingerprint output.
5. Запустить существующие context freshness/lock/capability smoke, сопоставить CLI/MCP через canonical Core и отдельный package-shaped чистый кандидат.
6. На code-assurance выполнить зарегистрированные pytest/Ruff lint+format/mypy для затронутой области, сверить D01-D11/R01-R12, заморозить кандидат и передать independent reviewer.
7. После PASS селективные commit/push/readback обеих dev; сохранить OOP54-55 и unrelated state. Отдельная честная alpha readiness оценка.
8. Native process закрывается только при выполненных obligations; installed/connected proof не подменяется source или stdio.

## architecture-plan-ready
Точные product paths уже разрешены immutable capsule. D01/D02/D05/D06/D07/D09/D11 и R03/R06/R07/R10/R12 учтены в domain.md/python-knowledge.md.
Контрольные тесты проверяют исправляемое поведение; широкий новый framework и необязательный audit не вводятся.

