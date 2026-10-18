# План публикации ProcessForge 1.2.0

Это конкретные материалы к решению о выпуске. Публичные операции этим документом не выполняются. Требование сопровождающего: docs/releases/1.2.0.md — public publication is pending qualification and explicit maintainer approval.

## Зафиксированная поставка

- Source commit: f975d3a7f54100c310bf3dced0f0bbbc256a7738.
- Source tree: 4e0255cb70b9bfbe9007ed4b78908e841c070b95.
- Будущий тег: v1.2.0 на этом exact commit.
- ZIP: processforge-1.2.0.zip,2538757bytes, SHA2566b4d3b8b5996c3cd26002884823066e973ef508ecc340ea651deaff6594c19ca.
- Sidecar: processforge-1.2.0.manifest.json, SHA256f56162602030be36115a39283d71f5ac5dad1533b0659b69ee186b41901db8ac.
- Локальные готовые файлы: .pf/tmp/pf120-stable-candidate-20261018/; источники только в отдельном чистом worktree.
- Описания выпуска: release-notes.en.md и release-notes.ru.md; migration guide уже входит в exact source/docs/releases/1.2.0-migration.md.

## Последовательность после решения сопровождающего

1. Проверить final full qualification receipts и текущее отсутствие конфликтующего v1.2.0/releases/assets. Создать отдельно scoped publication Work; текущая artifact-only Work не даёт разрешения изменять product/channel/infrastructure.
2. Создать v1.2.0 на указанном commit и отправить один и тот же tag в оба remote, с токеном для GitVerse. Прочитать оба tag refs и dereferenced commit полностью; не использовать force.
3. По maintainer contract собрать поставку из чистого checkout этого tag/commit. Native provenance не содержит имени tag; source epoch зафиксирован временем commit. ZIP обязан совпасть с проверенным SHA. После финальной сборки повторить проверку hash/parity и полный native extracted-archive test, как требует release-publishing.md; результаты текущей подготовки сохранить отдельно. Любые другие байты требуют нового фактического hash, согласования всех ссылок и повторной qualification до публикации.
4. Создать GitHub Release v1.2.0 с проверкой существующего tag, готовым EN описанием, ровно ZIP и sidecar. Не заменять существующие assets автоматически. Скачать опубликованные bytes и проверить ZIP/sidecar SHA, размер, manifest contents и source commit/tree.
5. Только после immutable asset readback применить publication-metadata.patch в чистом Work checkout от текущего доставленного dev head. Сырой patch сохранён в .pf/tmp/pf120-stable-candidate-20261018/; переносимая копия publication-metadata.patch.gz распаковывается обычным gzip/stdlib gzip без изменения bytes. Patch добавляет historical sidecar, обновляет mutable feed и две существующие release metadata expectations/checksum entries. Он намеренно не изменяет уже выпущенный tagged payload; предотвращает self-reference.
6. Повторить существующие metadata smokes, native checksum/schema и настоящую tag provenance с v1.2.0. На preview source binding проверен через exact commit; это не доказательство ещё не созданного public tag. Проверить actual release date/generated_at, если публикация состоится позднее подготовленной даты.
7. Отдельный metadata commit, parallel push обоих dev remotes и полный SHA readback. Прочитать публичный stable feed с нового endpoint state и проверить его final URL/hash against actual published assets.
8. Проверить discovery настоящим previous1.1.0 client через опубликованный HTTPS feed. Изолированный file-provider сценарий уже подтверждает совместимость формата и выбор1.2.0 с migration_required=true; live HTTPS readback нельзя подменять этим preview.

Установка не входит в публикацию. Клиент обнаруживает доступный artifact с SHA, но apply по-прежнему требует --confirm; controlled SQLite history cutover и host lifecycle остаются отдельными операторскими действиями. Действующее устройство повторно не обновлять ради публикации.

## Проверяемый состав metadata follow-up

- release/1.2.0/processforge-1.2.0.manifest.json: historical copy final sidecar.
- release/updates/processforge-stable.json: только действующая1.2.0; historical1.1.0sidecar сохраняется.
- tools/release_metadata_contract.py: existing expected version/tag1.2.0.
- tools/smoke_stable_update_manifest_points_to_release.py: existing1.2.0 asset/size/SHA expectation, убрана прежняя строковая блокировка легитимной1.2.0; exact single-version helper продолжает исключать другие версии.
- checksums/processforge.sha256: ровно две соответствующие QA entries.

Предлагаемые asset URLs находятся в proposed feed и promotion-materials.json. Старое специально переизданное1.1.0 не исправляется этой поставкой. Windows/device qualification и ограничения остаются в итоговом report; публикация не объявляет полное завершение OOP или проверку всех платформ.
