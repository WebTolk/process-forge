# Planning-only: общий приоритетный список

2026-10-22. Поручение: определить пересечения новых задач и рефакторинга и составить общий список по убыванию приоритета и сложности при появившихся лимитах агентной работы. Номинальные квоты/сроки неизвестны; сложность относительная.

Work: garage-pf-priority-overlap-plan-20261022-planning-only-consolidation-of.
Assignment: pf-priority-overlap-plan-20261022-planning-only-consolidation-of-current.
Context: pf-priority-overlap-plan-20261022-planning-only-consolidation-of-current-capsule.
Capsule checksum: 424b6603d3fb202bd9fe8884aea13e95d5c764fac2a618e3b00ef5afa4a20936.
Context snapshot: ctx-20261021-162229-c46ea2; current fresh/continue, valid/ready.

Разрешены чтение и только собственные report artifacts/log. Запрещено изменение продукта; worker/infra/actions не требуются. Исторические Work, source WIP, user priorities и task DAG не меняются. Режим planning_only; специализированный процесс software-feature-development@1.2.1, компактная фиксация применимых стадий и not_applicable для реализации.

Порядок: metadata inventory точных новых карточек и пяти OOP epics; successor/status reconciliation; текущий остаток 54–55; точечное чтение существующих owners/callers; map пересечений, dependencies и дублирующихся результатов; относительная сложность и предложенные приоритеты; сверка полноты/ordering, review собственного планового результата и document-only delivery. Никаких новых архитектурных или продуктовых контрактов не утверждается.

Критерии: каждая применимая зарегистрированная новая карточка представлена либо явно вычтена как завершённая; пять OOP epics покрыты без объявления полной миграции; технические общие файлы названы; программы сложности5 разделены на будущие этапы; приоритеты отделены от native статуса и непосредственного порядка исполнения. Tests/docs рассматриваются с затрагиваемыми owners. Действия и estimates не обещают конкретное число часов/токенов без измерений.

Материалы: report.md, roadmap.json, source-pins.json; private raw inventory сохранён локально. Источники перечислены в roadmap.json. Source чтение использовало Serena; metadata-only PF resource resolve подтверждён; PF search project artifacts не покрывает и это учтено. Общий development-flow legacy skill не применялся: действия управляются native PF. Тесты продукта для документального planning результата неприменимы; проверяются JSON coverage/sort/dependency integrity, ссылки и scoped diff.

