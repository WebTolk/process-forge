# T07: содержательная проверка после подготовки документов

Вердикт: **pass для design-only scope**. Проверено основным агентом после implementation; независимый reviewer не привлекался согласно single-agent process. Открытых блокирующих противоречий в пределах T07 не найдено. Это не аудит реализованного engine и не квалификация isolation.

| Предмет | Вывод и основание |
|---|---|
| Authorization/disclosure | Domain rule 1 и architecture steps 1–3 сохраняют scope denial; A24 проверяет невозможность получить новые права redaction |
| Начальная и дальнейшая выдача | Отдельные payload_only/mediated_session contracts; A05–A08/A26 требуют закрытия native reads/env/children/network, неизвестный route unsupported |
| Policy и intent | Предложен successor v2, без правки v1; pinned/current intersection и правила revocation/endpoint binding есть; A10/A23 |
| Неизвестные данные | Unknown/binary/timeout не превращаются в public; whole-unit и budgets перечислены; A04/A15 |
| Обязательный смысл | Domain и specification блокируют semantic loss; optional omission ограничен; A03/A21/A25 |
| Dispatch и audit | До выпуска обязательная durable receipt; ошибки после возможной передачи означают delivery_unknown, не safe retry; A11–A13 |
| Credentials и метаданные | Отдельный локальный channel, классификация имён/IDs/errors, private map не экспортируется; A20/A22/A27 |
| Immutable history | A19 сохраняет original bytes/hash и original doctor FAIL; новые view/export имеют собственную оценку |
| False positives/parity | Узкое исключение не отменяет true-secret/locked/scope deny; parity при одинаковых permissions, отдельно intentional recipient differences; A16–A18 |
| Пределы обещаний | Нет готовой isolation/анонимности/SLA; 31–52 дня явно предварительны, I01 может закончиться unsupported |

Замечания для будущей реализации, не дефекты документной поставки: определить backend/ОС, policy owner/registry, detector corpus и требования ACL/retention; проверить proposed budgets измерениями; проверить точную точку атомарной авторизации/nonce/budget при гонках revocation и dispatch. Спецификация уже задаёт безопасный исход при отсутствии capability или классификации; архитектура реализации должна доказать его.

Границы механической проверки: документный checker проверяет структуры и ссылки, а не эффективность detectors или фактический трафик. Он подтверждает полноту трассировки, но содержательная пригодность каждого test oracle оценена отдельно чтением матрицы. Runtime cases остаются not_run.

Not applicable: browser verification, product build, packaging, install, external model call. Причина — только документация в собственном .pf scope; соответствующие будущие проверки прямо включены в implementation plan. Исторический metadata finding не закрыт ремонтом, source code не менялся.
