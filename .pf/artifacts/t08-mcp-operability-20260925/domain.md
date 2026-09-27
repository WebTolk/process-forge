# T08 — domain notes / model / rules

## Модель

Source tree -> clean candidate -> archive manifest -> installed Core -> loaded MCP process. Workplace хранит registrations/runtime state отдельно; project .pf хранит snapshot/Work отдельно. Одинаковый VERSION не означает одинаковый build; release identity определяется commit и SHA256. Классификатор состоит из содержимого и стабильного provenance, независимого от физического расположения дистрибутива.

## Инварианты

1. Freshness не ослабляется. Реальное изменение классификации остаётся stale.
2. Sessionless Garage не требует Ledger; session-bound API не принимает отсутствующие/чужие session.
3. MCP stdout только JSON-RPC; splash/диагностика не добавляются в stdio T08.
4. Owner manifest ограничивает update. Unknown files, Workplace и project state не принадлежат заменяемому Core payload.
5. Процесс, уже загрузивший Core, не становится новым после записи файлов. Требуется новая MCP связь.
6. Source tests, archive tests, installed tests, live host tests — разные свидетельства, не взаимозаменяемые.
7. Оператор разрешил installed update и предложил session restart. Реальный host acceptance после restart обязателен до закрытия Work.
