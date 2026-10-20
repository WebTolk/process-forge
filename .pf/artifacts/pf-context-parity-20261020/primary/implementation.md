# Реализация: общая проверка official pack fingerprints

## changed-files
- src/processforge_core/project/source_check.py: общая политика принимает доказанное LF/CRLF представление только для official-process-pack.
- src/processforge_core/project/snapshot_sources.py: один обход выбранных official sources, общий прежний resolver workplace manifest, read-only probe raw/LF/CRLF digests.
- tests/context_parity/conftest.py и test_official_pack_freshness.py: meaningful Core regressions без legacy/transport.
- docs/{ru/,}concepts/context-resolution.md: объяснение правил и диагностики расхождения.
- checksums/processforge.sha256: изменены только четыре строки собственных поставляемых файлов, сохранены прежние pending rows.
Точная текущая фиксация байтов: candidate.json.

## change-summary
Recorded fingerprints и общая FileDigestReader остаются прежними. Для official mismatch повторный probe должен подтвердить ранее наблюдённый raw digest и эквивалентность LF/CRLF; наблюдённый drift между чтениями не теряется.
Active pack selection, source order, safe display, added/removed/error strings и границы других source kinds сохранены.
Общее Core правило используется существующими CLI/MCP consumers; изменений транспортных API нет.
Constructors остаются холодными, никаких межоперационных кешей и Main callbacks.
Явная scoped style-операция применила Ruff fix imports и format к четырём затронутым Python-файлам; последующие lint/format checks PASS.

## Проверки итерации
regression-before.log зафиксировал два направления исходного false stale до правки.
На текущих Python bytes: 16 passed, 4 subtests; Ruff lint PASS, format PASS; mypy PASS для четырёх файлов с ограниченным follow-imports; версии в iteration-checks.json.
Coverage всего Core не заявляется. Интегрированная assurance, независимое ревью и clean delivery proof следуют текущей стадией.

## implementation-scope-respected
Продуктовая запись ограничена exact grants. Pending OOP54-55 и прежние source bytes вне собственной области не менялись; их private baseline сохранён.
Инфраструктурная установка/reload и alpha publication не выполнялись и не принимаются этими исходными проверками.
Следующий этап: integrated assurance, independent review после frozen candidate, selective delivery и alpha readiness.

