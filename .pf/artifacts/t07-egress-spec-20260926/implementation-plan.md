# T07: отдельный план реализации и оценка

Это будущий план, не разрешение начать реализацию в T07. Текущий результат — спецификация. Оценка дана в инженерных рабочих днях одного разработчика с отдельным временем содержательной проверки в соответствующих срезах; календарные сроки и доступность внешних систем не обещаются.

Предпосылки: существующие T01/T05 contracts сохраняются; один backend и одна ОС для первой квалификации; текст/JSON, без бинарных данных/архивов и streaming; локальный policy/detector registry; fake recipients в автоматических тестах; реальные внешние модели не нужны для доказательства Core policy. Конкретный installed/connected маршрут проверяется отдельно от source unit tests. Изучение API стороннего executor и актуальной документации потребуется при выборе backend, до заявления capability.

| Срез | Результат и граница | Зависит от | Оценка |
|---|---|---|---|
| I01 | Feasibility одного backend/ОС: file/env/home/plugin/children/network ограничения и bypass prototype; выбор route или документированный unsupported | Новый scoped implementation Work и выбранный backend | 3–5 дней |
| I02 | Versioned v2 intent/egress binding, successor migration, v1 compatibility и reader rejection | I01, D03 | 3–5 дней |
| I03 | Policy resolver, bounded text/JSON classification, allow/redact/block, exceptions, semantic-loss rules, budgets | I02, утверждённый synthetic corpus и detector bundle | 5–8 дней |
| I04 | Immutable outbound views, opaque references, local map, pre-send audit, nonces и crash outcomes | I03 | 4–6 дней |
| I05 | File/tool broker с повторной authorization, current deny и безопасным source handle; credential separation | I04, выбранный backend contract | 4–7 дней |
| I06 | Один mediated remote transport и isolated-local/fake recipient fixture, явные unsupported маршруты; qualification backend | I01, I05 | 5–9 дней |
| I07 | Derived export, локальная provenance linkage, legacy metadata regression; без переписывания original | I04 | 2–4 дня |
| I08 | Adversarial tests, false-positive corpus, parity, fail injection, performance bounds, source/archive/installed/connected acceptance | I02–I07 | 5–8 дней |

Сумма: **31–52 инженерных дня**. Плановая неопределённость зависит прежде всего от I01; если backend не закрывает каналы, строгий маршрут остаётся unsupported, а оценка реализации нового isolation backend выполняется отдельно. Новый sandbox с нуля, несколько ОС, дополнительные providers, UI/T10, remote web, юридический анализ и внедрение готового enterprise DLP сюда не входят. Это диапазон предварительной оценки, не замер и не обязательство по срокам.

Последовательные точки решения:

1. После I01 выбрать: подтверждённо реализуемый mediated route; ограниченный `payload_only` с честной маркировкой; либо завершить feasibility без строгого route. Снижение запрошенного уровня нельзя делать автоматически.
2. После I02 зафиксировать версию контрактов и миграционный corpus. Нельзя начать незаметно добавлять security intent в v1.
3. После I04 проверить отсутствие bytes у fake recipient при любом denial и audit failure; после I05 — после начального prompt при повторных reads/tools.
4. После I06 отдельно квалифицировать environment/backend и версии. Application tests не подтверждают запрет всех обходных каналов.
5. После I08 выпускать лишь доказанные capabilities. Данные реального проекта/реальные secrets не нужны в adversarial corpus. Доступ к внешнему endpoint должен следовать scope нового Work, а не разрешению на этот документ.

Минимальные критерии реализации: полное покрытие [матрицы](acceptance-matrix.json), ноль synthetic secret leaks в проверяемом corpus; 100% блокирование mandatory deny/failure сценариев; отдельно измеренная доля false positives на заранее размеченном benign corpus и документированная utility после redaction; одинаковые решения local/remote при одинаковых policy/data/permissions и объяснимые различия recipient policy. Нулевые утечки в corpus не равны доказательству отсутствия всех возможных утечек.

Производительность: измерить latency/memory в I03/I08 на согласованной ОС и размерах 1 KiB, 64 KiB, 1 MiB. До измерений из T07 нельзя выводить SLA. При превышении установленного лимита strict передача блокируется; лимит можно изменить только явным versioned contract, не пропуском проверки.

Первый будущий assignment: I01, backend feasibility, с синтетическими данными и отдельным file scope. После выбора backend пересчитать I02–I08 и подтвердить необходимые toolchain/platform contracts. Не начинать product implementation из нынешнего T07 и не смешивать её с установкой Core/Runtime.
