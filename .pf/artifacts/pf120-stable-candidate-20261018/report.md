# ProcessForge 1.2.0: проверенный кандидат

Квалификация исправленного кандидата завершена. Исходники, supervisor-stress и точный распакованный ZIP прошли обязательные полные проверки. Work штатно завершена; task/run/runtime-events/continuation doctors прошли без ошибок. Публичная публикация ожидает отдельного решения сопровождающего.

## Точная поставка

- Source: `f975d3a7f54100c310bf3dced0f0bbbc256a7738`; tree `4e0255cb70b9bfbe9007ed4b78908e841c070b95`, чистый detached LF worktree.
- [ZIP](../../tmp/pf120-stable-candidate-20261018/processforge-1.2.0.zip): 2538757 bytes,1309 записей, SHA256 `6b4d3b8b5996c3cd26002884823066e973ef508ecc340ea651deaff6594c19ca`.
- [Отдельный native sidecar](../../tmp/pf120-stable-candidate-20261018/processforge-1.2.0.manifest.json): SHA256 `f56162602030be36115a39283d71f5ac5dad1533b0659b69ee186b41901db8ac`; находится вне ZIP.
- В сравнении с принятой dev-поставкой изменились только локальный индекс обновлений, его checksum и generated Core manifest. Остальные1306 записей, включая исполняемый код, совпадают. Все байты и hashes проверены: [identity](archive-identity.json).

Несоответствие `VERSION1.2.0` и локального `self-update-check CURRENT1.1.0` исправлено отдельной завершённой Work: [отчёт](../pf120-local-update-index-20261018/report.md). Шесть проверок подтверждают согласованность1.2.0 в исходниках и ZIP, а для предыдущей1.1.0 — доступное обновление с руководством миграции. История версий и официальный endpoint сохранены.

## Проверки

| Проверка | Результат | Доказательство |
| --- | --- | --- |
| Полный native source --public | 274/274PASS и3 public checks PASS; 1627.870s | [полная матрица команд](source-full-results.json) |
| Native supervisor-stress | 6/6PASS, точный порядок; 156.222s | [результаты](supervisor-stress-results.json) |
| Полный native consumer точного ZIP | PASS, оба CLI entry points и полный extracted release-test; 1499.685s | [consumer](archive-consumer-results.json) |
| Состав и происхождение | Все1309 записей; чистый source/commit/tree/epoch; private/derived entries отсутствуют | [identity](archive-identity.json) |
| Локальная версия source/ZIP | 6/6PASS | [coherence](local-version-coherence.json) |
| Проект метаданных публикации | 6 положительных проверок,7 ожидаемых отказов; patch apply/whitespace PASS | [сводка](metadata-qualification.json) |
| Клиент опубликованной1.1.0 | Находит точный URL/SHA1.2.0 и миграцию; оба apply требуют подтверждения до изменения файлов | [previous client](previous-client-discovery.json) |

Все полные прогоны выполнены последовательно на исправленных байтах без выборочных исключений. Source-команды сопоставлены с полным штатным каталогом в точном порядке. Consumer подтверждён собственным штатным полным запуском; CLI не сохраняет его успешный внутренний вывод и временный подробный отчёт. Результаты прежнего c4d-кандидата сохранены в [baseline](baseline-c4d/README.md), включая намеренно прерванный consumer; новому кандидату они не засчитываются.

## Комплект публикации

[Порядок публикации](publication-plan.md), [EN notes](release-notes.en.md), [RU notes](release-notes.ru.md), [полные предлагаемые файлы](publication/README.md), [точный patch](publication-metadata.patch.gz), [identities](promotion-materials.json), [primary review](review.md).

Проект последующего metadata commit затрагивает ровно пять путей: historical sidecar1.2.0, stable feed, две существующие QA-проверки и их checksum inventory. Все URL/hash/size относятся к текущему ZIP. Raw diff сохранён без изменения байтов в gzip; полные файлы доступны для чтения. В действующий канал он не применён. Историческая специально переизданная1.1.0 сохранена; все933 записи фактически опубликованного предыдущего архива проверены для изолированного сценария.

Требуемый порядок после разрешения: тег `v1.2.0` на указанном source commit, неизменяемые assets и проверка скачанных hashes, отдельный metadata commit/stable channel, затем обнаружение предыдущим клиентом через опубликованный HTTPS feed. Текущие проверки file-provider и привязки к commit не заменяют будущие public tag/HTTPS проверки.

## Границы

Это промежуточная точка ООП-рефакторинга. Проверки Windows/current Python и штатных fixtures не подтверждают Linux/macOS, все версии Python или новый запуск реальных внешних исполнителей. Ограниченная история остановки, неполные метрики и необязательные пути сохраняют свои описанные ограничения. Primary review выполнен без независимого агента: капсула запрещает subagents.

Установленная dev-поставка8ea152b и её прежняя [фактическая connected-host приёмка](../pf120-dev-release-20261017/report.md) остаются отдельными доказательствами. Установка нового кандидата и перезапуск служб не выполнялись. Публичные tag/assets/stable channel ожидают [explicit maintainer approval](../../../docs/releases/1.2.0.md); текущая Work готовит и доставляет проверенный комплект.


## Закрытие и доставка доказательств

PF вернул `run_completed`; assignment `done`, контекст valid/ready, блокировок нет: [closeout](closeout.json). [Doctоrs](doctors.json) проверили task, run с runtime-events и продолжения. Точный [handoff](../../handoffs/pf120-stable-candidate-20261018.md) сохранён; корректный путь к нему также указан в closeout вместе с навигационным уточнением для неизменяемого evolve-отчёта.

Комплект проходит финальную проверку JSON, личных путей, секретов и обычный Git whitespace gate. В отдельный evidence-коммит включаются только собственные артефакты и handoff. Этот поздний коммит не заменяет source commit кандидата: тег v1.2.0 должен указывать на `f975d3a7f54100c310bf3dced0f0bbbc256a7738`.

После параллельного push обеих dev-веток формируется локальная послекоммитная квитанция publication.json с полным SHA и фактическим чтением обеих refs. Она хранится отдельно от коммита, который проверяет. GitVerse обслуживается существующим token helper без секрета в URL, аргументах и артефактах. Действующий stable channel и публичные assets этим коммитом не изменяются.
