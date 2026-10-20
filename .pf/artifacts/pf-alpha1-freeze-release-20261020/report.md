# ProcessForge 1.3.0-alpha1 — заморозка и публикация

Опубликовано 2026-10-20 14:25 UTC:

- https://github.com/WebTolk/process-forge/releases/tag/v1.3.0-alpha1
- https://gitverse.ru/webtolk/process-forge/releases/tag/v1.3.0-alpha1

Оба релиза public, draft=false, prerelease=true. Тег v1.3.0-alpha1 на обоих
hosts указывает на source commit d32200700c48bdbf796728f01209798d40a986c6,
tree ac54f1b3b5281eee2bfd805abcbe4ac473383ba7. Это принятый dev checkpoint
с минимальными release blockers, без незавершённых OOP54–55 и чужих dirty/staged bytes.

ZIP: processforge-1.3.0-alpha1.zip, 2 794 326 bytes.
SHA-256: 71f8a16f95e1ce63cde3e7f9e3344b67734c14f85f631e8e392d93e46dbde7ea.
Native pack объявил 1461 entries. Использованы bytes единственной canonical
source-suite сборки; переупаковки не было.

Sidecar: processforge-1.3.0-alpha1.manifest.json, 265 811 bytes.
SHA-256: f6bf94bec5fe6ba6bd52979162901fae3bc6457a0a974673e3d07acdf4fe0f7f.
На GitVerse тот же JSON размещён как .manifest.json.txt; после скачивания можно
убрать .txt. Проверены все четыре удалённых файла и оба точных release id.
Черновики прочитаны по exact id; GitHub tag endpoint для draft возвращал 404,
создание не повторялось — существующий draft найден по точному tag в списке.

Квалификация: clean pytest17 PASS; public source suite 274/274 PASS без warnings;
supervisor-stress, шесть сценариев PASS. Ruff lint/format и mypy двух изменённых
Python файлов PASS. Точные команды, версии и ограничения — test-report.md,
code-quality-report.md, tool-versions.json и source-gates.json. Новый независимый
review не заявляется. Прежний typing debt Core не исправлялся.

Стабильный manifest сохранён побайтно, GitHub latest stable остаётся v1.2.0.
Новый release/updates/processforge-alpha.json — отдельная alpha opt-in подписка:
native schema PASS, discovery от 1.2.0 PASS, stable channel альфу не выбирает.
Historical sidecar копируется после source commit, без hash self-reference.
main не продвигался. Final metadata/evidence commit и readback обоих dev
фиксируются в собственном .pf/tmp/pf-alpha1-freeze-release-20261020/git-delivery.json.

Пределы: ZIP contents и release-archive-test не проверялись по прямому указанию
пользователя; удалённые файлы проверены как непрозрачные bytes по size/SHA-256.
Это Windows source/publication qualification, без новой установки на устройство,
Runtime/MCP reload или actual connected-host acceptance alpha. Эти действия
не входят в поручение. Дальнейший рефакторинг не возобновлялся.
