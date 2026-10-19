# Проверка публичного состава server-window задачи

Дата: 2026-10-19. Статус: ready_for_review. Исполнитель: primary.

Точная копия публичного состава содержит 1395 файлов без checksum inventory.
Все продуктовые bytes совпадают с рабочей копией. Единственное объявленное
отличие — .pf/process-forge.yaml из baseline Git commit
bd0d39b36055bc5ccf7a7bd4ba4639f4c3dfe71f: это сохраняет посторонние локальные
knowledge selectors и соответствует исходному tracked состоянию, которое
эта задача не меняет. Private historical assignments/capsules/runtime не копировались.

Полные размеры, raw SHA-256, release SHA-256 и origin каждого файла записаны
в public-view-manifest.json. Нормализация release: CRLF -> LF для non-binary.
Повторная сверка всех working-source записей: изменений после freeze нет.

| Штатная проверка временной публичной копии | Результат |
| --- | --- |
| validate-process-forge-schemas.py --root <public-view> | PASS, exit 0 |
| validate-public-cleanliness.py --root <public-view> | PASS, exit 0 |
| validate-process-forge-checksums.py --root <public-view> --check | PASS, exit 0 |

Финальные целевые проверки настоящих source entrypoints описаны в
../primary/focused-checks-final.md: 27 console tests, HTTP guards, Windows
autostart/MCP contracts и singleton/atomic-publication checks прошли без
подмены test source. У worker sandbox были TempDirectory ACL и child-liveness
ограничения; в родительском окружении canonical команды прошли.

## Изменения inventory

4 новых и 12 изменённых paths принадлежат текущей задаче. Дополнительно старый
inventory содержит два устаревших hashes для tools/release_metadata_contract.py
и tools/smoke_stable_update_manifest_points_to_release.py. Оба тела уже совпадают
с baseline commit до задачи; это доказано preexisting-inventory-drift.json.
Они не менялись. Штатная регенерация inventory может привести эти два hashes
к уже существующим bytes; это не расширение product scope. Неожиданных product
изменений и удалений нет. Исходный локальный PF config остаётся нетронутым.

## Пределы проверки

Первый запуск scratch helper остановился из-за отсутствующего пустого каталога
checksums; исправлена только подготовка helper, новая полная копия создана
отдельно и прошла проверки. Предыдущая копия остаётся диагностическим scratch.
Эта проверка не создаёт release ZIP и не устанавливает Core. Windows native
пробы подтвердили безопасный отказ при invisible nonclassic HWND; Linux GUI
недоступен. Успешная реальная минимизация Windows classic и Linux X11 не проверена.
Full dirty source schema/cleanliness findings сохранены как отдельный baseline,
а не объявлены исправленными. Независимый reviewer проверяет этот отчёт вместе
с primary и всеми четырьмя worker contributions.
