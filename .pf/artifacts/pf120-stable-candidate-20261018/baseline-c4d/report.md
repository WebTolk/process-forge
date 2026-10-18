# ProcessForge1.2.0: подготовка стабильной поставки

Статус: выполняется финальная квалификация кандидата. Полный source suite PASS; supervisor-stress выполняется, полный consumer suite ещё впереди. Публичные tag/assets/stable channel не изменялись.

## Точная поставка

- Source: c4d66496464179750aa0448d11e4d2e797c2d2ff; tree3f7a2eff97f9391efd71d548bcc841103d9baf53, чистый detached LF worktree.
- [ZIP](../../tmp/pf120-stable-candidate-20261018/processforge-1.2.0.zip):2538276bytes,1309entries, SHA2564bcd22509ff15bd4c46febd078e3da596da0f0bf6a9eeb4104b2b75ce6aaaa12.
- [Native sidecar](../../tmp/pf120-stable-candidate-20261018/processforge-1.2.0.manifest.json): SHA25637c7ff574819e56a673843052531c6838fc5a517ab3ec962fde3f5b1c2c22b62; остаётся вне ZIP.
- Все1308 негenerated payload entries побайтно равны принятому dev ZIP; отличается только generated Core manifest с новым source commit/tree/epoch. Его1308-file inventory прежний. Private/derived files отсутствуют.

Точные проверки: [archive-identity.json](archive-identity.json), [source-identity.json](source-identity.json). Прежняя установленная dev-поставка8ea152b и её [actual-host приёмка](../pf120-dev-release-20261017/report.md) — отдельные доказательства; новая установка ради этого кандидата не выполнялась.

## Квалификация

| Проверка | Результат | Доказательство |
| --- | --- | --- |
| Полный native source --public | 274/274 PASS,3 public checks PASS;1590.555s | source-full-results.json |
| Полнота source | Все команды из полного native catalog в точном порядке; без --only/--skip | source-full-results.json |
| Native supervisor-stress | ВЫПОЛНЯЕТСЯ | supervisor-stress.json после завершения |
| Native extracted archive full | ОЖИДАЕТ ЗАПУСКА | archive-public-full.json после завершения |
| Native pack/полная parity | PASS; generated manifest — единственный dev delta | archive-identity.json |
| Proposed normalized manifest schema | PASS | proposed-manifest-schema.json |
| Существующие metadata/checksum проверки | 5 PASS: inventory/surface/links/sidecar/source binding | promotion-*.json |
| Отказы неверных metadata | 7/7 ожидаемых отказов | promotion-metadata-refusals.json |
| Previous1.1.0 discovery и confirmation | PASS; native generic/Core apply отказаны без --confirm до записи | previous-client-discovery.json |

Это один полный успешный прогон точных финальных исходников, включая исправленную ранее constructor fixture. Исторический FAIL прежнего280e00d не скрывается и не выдаётся за новый результат. В исходной истории он закрывался test-only поправкой и consumer suite; текущая Work добавляет отдельный полный final-source PASS.

## Готовые материалы публикации

[Порядок публикации](publication-plan.md), [EN notes](release-notes.en.md), [RU notes](release-notes.ru.md), [proposed feed](publication/release/updates/processforge-stable.json), [metadata patch](publication-metadata.patch.gz), [promotion identities](promotion-materials.json).

Предлагаемый metadata follow-up затрагивает ровно пять путей: historical1.2.0 sidecar, mutable feed, две существующие release QA expectations и две их inventory entries. Он не применён к действующему каналу/исходникам. Readable final files хранятся в publication/, оригинальный diff сохранён без изменения bytes в gzip. Изолированные positive/negative проверки подтверждают соответствие actual ZIP hash/size/URLs и сохранение отказов.

Клиент взят из действующих публичных1.1.0 assets; все933 entries сверены с их фактическим sidecar. Старое специально переизданное1.1.0 не исправлялось. В изоляции previous CLI видит1.2.0, migration_required=true, точный proposed URL/SHA. Native update apply и core-update apply без подтверждения возвращают отказ; Core/fixture hashes не меняются. Этот file-provider сценарий не заменяет будущий HTTPS readback опубликованного feed.

## Границы и дальнейшее действие

Windows/current Python и текущие fixtures не объявляются матрицей всех платформ/версий Python. Bounded shutdown history, partial metrics и optional qualification limits остаются явными. Intermediate OOP checkpoint не означает завершение всей программы refactoring. Primary review выполняется после implementation; независимый агент запрещён immutable capsule.

После всех mandatory gates требуется native closeout/doctors и scoped evidence delivery в обе dev ветки. Только затем конкретный bundle передаётся на решение о публичной публикации: [release policy](../../../docs/releases/1.2.0.md) требует explicit maintainer approval. Порядок: exact tag -> immutable assets/hash readback -> отдельный metadata commit/stable channel -> HTTPS discovery previous client. Повторять device apply или server/MCP lifecycle не требуется.
