# Проверки перед установкой

## review-findings / test-plan
Принятый source commit 526c5d13 и archive acaa0ff8... неизменны. Независимое review
PASS/run_completed; все 7 candidate byte hashes повторно совпали. Новых source
Python правок нет, поэтому новый source review и повтор прежнего pytest/lint/typecheck
not_applicable. Тот же код, интерпретатор Python 3.14.3 и применимая среда сохранены.
Прочитаны python-quality-context.md и общий Python toolchain; docs.python:root
разрешён новой exact Work. Локальная Python документация уже использовалась при
реализации принятых байтов; для deployment новой языковой политики не требуется.

## test-cases / test-report
Переиспользованы именно прежние успешные native receipts: 16 pytest +4 subtests,
Ruff lint/format PASS, mypy PASS, три context smoke группы PASS, 4 adapter phases.
Команды/версии/exit codes в предыдущем primary/iteration-checks.json: pytest9.1.1,
Ruff0.17.1, mypy2.4.0; все exit0. Native plan текущего устройства exit0, blockers[],
нет локальных модификаций/удалений/миграций, сохранены текущие protection baselines.
После apply обязательны реальные installed CLI/hash/doctor и preservation checks.

## code-quality-report / assurance-complete
Новой исполняемой продуктовой области нет. Нужная проверка здесь — реальные
байты до/после установки и нативный результат; новый unit test для обёртки доставки
не нужен. Alpha release gate по-прежнему NO-GO: известны prerelease ordering и
missing Path import в прежнем smoke. Они не входят в пять changed device paths.
Это разрешённая установка исправления dev, без утверждения публичного alpha gate.
Content audit ZIP по указанию оператора исключён; native installer checks сохранены.
