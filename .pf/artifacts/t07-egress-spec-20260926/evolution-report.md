# T07: выводы и следующий ограниченный шаг

Evolution status: captured для проекта ProcessForge. Shared skills, process definitions, product code и память пользователя не изменяются. Уроки являются локальными предложениями для будущей реализации, не новыми установленными правилами.

| Наблюдение | Узкая область применения и целевое изменение | Основание |
|---|---|---|
| Разрешение чтения prepared resources не является разрешением раскрытия | Будущий Core egress contract и tests; сохранить независимые проверки | Investigation, A01/A24 |
| Безопасный initial payload не покрывает последующие native reads | Capability contracts конкретного backend, отрицательные обходные тесты | H02/H03, A05–A08/A26 |
| Public metadata проверки и immutable history могут иметь разные исходы у original и derivative | Будущий export view и regression metadata fixture; не править старый intent | H12/H13, A19/A20 |
| Внешний receipt не должен раскрывать private source hashes и имена | Audience-specific audit/export allowlists | H09/H13, architecture audit section |
| Interrupted send нельзя считать безопасным повтором | Будущий dispatch state machine и fault injection | H06/H11, A11–A13 |

Следующий scope реализации: **I01 feasibility одного backend/ОС**, синтетические данные, проверка file/env/home/plugin/children/network каналов и выполнимости broker-only пути. Результат — конкретная evidence matrix и решение supported/unsupported; ещё не универсальный privacy engine. После выбора backend пересчитать I02–I08, загрузить соответствующие local platform/toolchain contracts и открыть отдельно ограниченную реализацию. Исходная оценка 31–52 инженерных дня исключает разработку нового sandbox с нуля.

Другие задачи roadmap не поглощаются T07. T10/terminal UI и remote web остаются за её границей. Установленная инфраструктура не затронута, старые capsules и зарегистрированные artifacts защищены, старый metadata finding не закрывается изменением истории.

Для новой сессии: прочитать `.pf/AGENTS.md`, актуальные manifest/context и T07 handoff; не запускать заново завершённую T06/T07 и не доверять одному generated historical report вместо текущего Work state. Сохранять различие между документной приёмкой, source tests, installed package и connected execution proof.

Handoff on completion: итоговая спецификация, домен/угрозы/архитектура, отдельный план и future acceptance matrix готовы. Выполнить финальный installed run-doctor и проверку девяти stage evidence/capsule hashes; записать финальное наблюдение и продолжение без изменения уже принятых файлов.
