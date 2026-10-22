# Приёмочные примеры и будущие проверки

Это спецификация будущих тестов, не отчёт о работающем продукте. В планировании арифметика контрольных примеров проверяется отдельно; collectors/БД/transport ещё не реализованы. R-ссылки относятся к `domain.md`.

| ID | Вход / действие | Ожидаемый результат |
| --- | --- | --- |
| A01 | Input_total=1000, cache_read=600; output_total=200, reasoning=80. | Всего1200, а не1880; cache/reasoning — подкатегории. R05. |
| A02 | Современный Kimi: inputOther=100, cacheRead=500, cacheCreation=50, output=200. | Input_total=650, total=850; неизвестный reasoning=null. R05. |
| A03 | Та же occurrence/revision доставлена дважды; затем тот же key с другим hash. | Первая учтена один раз; несовпадение — conflict, не второе списание. Две разные настоящие occurrence с одинаковыми числами обе учтены. R04/R09. |
| A04 | Snapshot unit output40 -> revision2 output60 -> запоздавшая revision1. | Выход60, не100 и не40; повтор2 не меняет итог. Две разные receipts output40+60 дают100. R07. |
| A05 | Session cumulative baseline1000 ->1300 ->1400, повтор1400; затем reset без доказанного epoch. | Новые токены400; reset partial/unknown, без отрицательного расхода или истории, записанной в текущую задачу. R08. |
| A06 | Современный Kimi usage.record: turn delta850 и session delta50; отдельный status summary900. | Измеренный расход900; summary повторно не добавляется, session delta50 не теряется. Конкретная версия/семантика подтверждается реальным fixture. Не выводить эту семантику из слова session. R08/R09. |
| A07 | PreCompact token_count12000; PostCompact estimated_token_count3000; compaction request receipt input1000/output100. | Compaction usage1100; размеры12000/3000 не прибавляются. Если request receipt отсутствует — gap compaction, не ноль. R06/R10. |
| A08 | Failed attempt даёт150 токенов, успешный retry850; ещё один оборванный запрос без usage. | Наблюдаемый итог1000 + один missing/partial, а не850 или «полный итог1000». R10/R16. |
| A09 | Agent A работает10:00–10:10; B10:05–10:15. Внутри A есть request10:02–10:04. | Agent time20min; occupied15min; nested request не добавляет ещё2min. Одновременные A/B10:00–10:10 дают20/10. R11/R12. |
| A10 | Интерактивные turns10:00–10:02 и11:00–11:03; сессия открыта весь день. | Agent time5min; час ожидания пользователя не учитывается как исполнение. Approval ожидание выделяется лишь при известных событиях. R11/R12. |
| A11 | Worker старт10:00, последнее подтверждение10:03, пропал без end; просмотр в13:00. | Подтверждённое время/нижняя граница до10:03 с partial, не3часа. Незавершённый хвост не выдумывается. R13. |
| A12 | Project доказан, task не доказан; session меняла две задачи. | Расход в project-unassigned, без копирования полного session total в обе задачи. Неизвестен проект — вне его итогов. Unit пересекает смену binding — unassigned/partial, не пропорциональная догадка. R02/R08. |
| A13 | Два разных project UUID имеют одинаковое имя; project перемещён по другому local path. | Разные UUID не сливаются автоматически; перемещение сохраняет историю при существующем mapping. Межустройственное объединение только по явной регистрации. R03. |
| A14 | Родитель содержит child summary300 и собственный usage700; child journal содержит те же300. | Всего1000, не1300; collectors доказывают coverage и canonical child identity. R04/R09. |
| A15 | Известный тариф: input uncached400 по2USD/M, cached600 по0.5USD/M, output200 по8USD/M; reasoning80 уже в output. | Оценка0.0027USD:0.0008+0.0003+0.0016. Тариф вымышленный для проверки формулы; не текущая цена какой-либо модели. R14/R15. |
| A16 | Одна запись имеет provider-reported0.003USD и tariff estimate0.0027USD; другой проект0.1EUR; скрытая модель без rate. | Отдельные basis/валюты; не0.0057USD и не USD+EUR. Unknown model не подменяется «похожим» тарифом. Подписка не превращается в реальное API-списание. R14/R15. |
| A17 | Появилась новая rate version; запрос старого valuation; затем явный revalue. | Старый результат воспроизводим по закреплённой версии; новая valuation сохраняется отдельно с provenance. Нельзя молча менять исторические расходы. R15. |
| A18 | Collector/SQLite прервался между чтением и commit; повторный batch, конкурирующая доставка. | Facts/cursor атомарны, пропуска/дубля нет при replayable source. На конфликт/lock bounded retry/error; worker exit прежний, coverage показывает gap. Не обещать восстановление потерянного нереплицируемого source. R09. |
| A19 | В источнике нет поля cached; присутствует явно измеренный output0; два источника поддерживаются, один отсутствует. | Cached=null/unsupported, output0 допустим; coverage сообщает отсутствующий источник, subtotal не назван полным. R05/R16. |
| A20 | Период10:05–10:10, activity10:00–10:15, receipt timestamp10:12. | Время5min, receipt вне периода; токены не делятся произвольно на трети. Late receipt меняет as_of. R17. |
| A21 | Повторный sync/relay того же origin/fact/revision; REST недоступен; восстановлен backup. | Один вклад на receiver, локальный учёт работает offline. Для cloned devices отдельная write origin при сохранении origin старых фактов; проектные агрегаты не отправляются как новые расходы. Будущая задача sync. R03/R18. |
| A22 | Read-only task consumer; запрос другого проекта/raw log; включение sync без project allowlist. | Нет расширения доступа; в DTO/export нет private paths, prompts, credentials. Sync opt-in только с согласованным scope. R18. |

Будущая автоматизация: unit-тесты доменных правил/Decimal/интервалов, contract fixtures на реальные receipts, SQLite integration для транзакций/конфликтов/параллельного приёма, bounded incremental reader для partial JSONL/rotation/truncation/replay, CLI/MCP contract tests и source qualification. Приёмка клиента включает main agent, child agents, failure и compaction, а не только счастливый один turn. Remote/TUI/plugin проверки выполняются в их отдельных задачах.

Приёмка документов текущего цикла: все ссылки на артефакты существуют; YAML исходной карточки валиден и остаётся open/planning_only/writer=false; меняется только input reference; контрольные числа A01/A02/A04/A05/A06/A08/A09/A10/A15 пересчитаны; код продукта и чужой WIP сохранены. Самопроверка primary не называется независимым code review.
