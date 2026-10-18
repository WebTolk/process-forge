# Исправление локального индекса обновлений1.2.0

Результат: PASS для узкой source-only задачи. Команда self-update-check теперь по умолчанию показывает CURRENT1.2.0/LATEST1.2.0/UPDATE none. Для явно указанной1.1.0 доступна1.2.0 с обязательным ознакомлением с migration guide.

Изменены только updates/processforge-update-index.yaml и соответствующая запись checksums/processforge.sha256. Добавлена запись1.2.0 с датой checkpoint из CHANGELOG и существующим docs/releases/1.2.0-migration.md. Пять исторических записей и официальный manifest endpoint сохранены. Код CLI, тесты, parser/runtime, process/schema/capsule versions и active online stable feed не менялись.

Проверки: targeted-checks.json; native schema/cleanliness/checksum/release-check receipts — все exit0. Устаревший проект проверен в отдельном fixture; действующая среда не изменялась. Canonical YAML SHA256f19ae25b1164792fce4ade226f4a9fcb9e5e46c339f4c7d2ec3cdbbcecfe11e7, изменена ровно одна inventory entry.

Primary review: review.md. Полная квалификация нового release candidate выполняется родительской Work отдельно; прежние c4d6649/4bcd2250 остаются baseline и не подменяют новые bytes. Публичные tag/assets/channel и device lifecycle в этой задаче не выполнялись.

Native completion/doctors и точный отдельный commit/dual readback фиксируются в closeout.json и publication.json. Unrelated dirty/index state и immutable input capsules сохранены.
