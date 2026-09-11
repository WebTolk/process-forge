# Исправление документации PF перед 1.1.1

Дата: 2026-09-07. Оркестратор: основной агент. Статус: D01-D08 исправлены и приняты; независимое ревью PASS. Общая готовность к релизу НЕ подтверждена: полный source release-test выявил отдельный воспроизводимый отказ исходного HEAD.

База: dev, HEAD 1aecc18b6824204ca45ab30241b92d26e6d583a5 плюс сохранённые незакоммиченные изменения required_output_checks. План: plan.md и orchestrator-plan.yaml; модели уточнены в model-routing-amendment.md. VERSION остаётся 1.1.0. Это подготовка документации, не выпуск 1.1.1.

## Закрытие замечаний аудита

| Замечание | Исправление | Доказательство |
| --- | --- | --- |
| D01 | RU search-index использует Workplace, удалены пять неподдерживаемых --project-root; уточнены индекс и refresh | mechanical-review.md; docs-contract-integrated.json |
| D02 | Обычный task-batch prompt ведёт через context/search/resolve/start/state/transition; низкоуровневые команды только по явному запросу | workflow-review.md; manual-infra-final.json |
| D03 | EN/RU пример завершает обе блокирующие задачи и Run; указаны два необходимых official packs и операторская граница настройки | documented-batch-final.json: исполнен пример EN в изолированной fixture, обе задачи и Run completed |
| D04 | EN/RU MCP-справка описывает process_id, process_choice_required, рекомендательный default и pin существующего Run | workflow-review.md; текущая реализация выбора процесса; отдельный multi-process-final.json |
| D05 | required_outputs — список явных записей id/path/type/required | mechanical-validation.json; новый smoke вызывает текущую нормализацию; frontmatter-runtime.json: missing до создания файла, PASS после |
| D06 | RU plan/apply запрашивают Workplace migration; сохранены пользовательские настройки, post-update doctors, linked-project checks и recovery | update-review.md; core-update-contract.json PASS в изолированных fixtures |
| D07 | EN/RU описывают полный цикл state/transition до run_completed, реальные поля и записи evidence, допустимые gate statuses и отказ без продвижения | workflow-review.md; новый smoke сравнивает gate statuses с текущим _gate_state |
| D08 | Checksum check отделён от --write и проверок контекста; добавлены исполняемые context/capsule doctor примеры | mechanical-review.md; docs-contract-integrated.json |

Дополнительная найденная проблема: EN/RU README ссылались на dist/processforge.zip, отсутствующий внутри дистрибутива. Ссылка заменена именем архива и точным пояснением места локальной сборки. Portable-copy проверка первоначально выявила дефект, повторная прошла.

## Приёмка и контроль воркеров

Механические исправления делегированы gpt-5.3-codex-spark; связанная документация — gpt-5.4-mini; тесты после отклонённой первой попытки — gpt-5.6-luna; независимый reviewer — gpt-5.6-luna. Все запускаются конечными shell-процессами через codex-exec, без запуска/ремонта PF инфраструктуры. Файловые области не пересекаются. Журнал: .pf/logs/docs-fix-1.1.1-orchestrator-20260907.md.

Все пять делегированных задач имеют статус done; блокирующих незавершённых задач этого исправления нет. Scoped run-doctor оркестрации прошёл. Это завершение работы по документации, а не снятие отдельного предрелизного блокера.

Результат воркера не принимался по одному exit 0. Сохранены попытки и сырые отчёты; основной агент исправил неверную форму required_outputs, лишние переписывания RU, ошибочный fallback на compatibility, неверные evidence-примеры и ссылки. В тестах отклонены зависимость от приватного assignment и обход временных папок. После завершения писателей оформление передачи владения — *-review.md в этой папке. Созданный воркером временный каталог перенесён под .pf/tmp и сохранён как свидетельство отклонённой попытки; пользовательские данные не удалялись.

Подтверждено:

- docs-contract-integrated.json: PASS, 610 CLI-примеров разобраны текущим argparse без диспетчеризации, 297 локальных файлов-целей существуют.
- portable-docs-integrated.json: PASS, новый regression smoke выполнен из копии 931 публичного файла без .pf и Git.
- readiness-final.json: PASS, устранён устаревший аргумент search-index; исходные проверки readiness сохранены.
- manual-infra-final.json: PASS; прежнее покрытие templates, AGENTS и core source сохранено, добавлен специализированный prompt.
- documented-batch-final.json и core-update-contract.json: PASS, изолированные исполняемые проверки.
- schema-check.json, cleanliness-corrected.json, checksum-check.json, integrated-diff.json: PASS. cleanliness-check.json сохраняет ошибочный вызов отсутствующего имени скрипта; корректный валидатор был затем найден в release registry и выполнен успешно.

Независимое ревью: docs111-review-report.md — PASS, actionable findings отсутствуют; review-adjudication.md исправляет устаревшее ограничение readiness из сырого отчёта. Исходники reviewer не менял.

Полный source suite: **RESULT: FAIL, 102 PASS / 1 FAIL, 924.932 секунды**. Команда: python -u tools/processforge.py release-test --no-clean --trace-smokes --fail-fast. Очистка существующих release artifacts не запрашивалась. Пройдены все проверки документации, новый smoke, прежние required-output регрессии и исправленная readiness-проверка. Отказ — smoke_garage_no_hooks_sessionless: empty_corpus вместо одного ресурса. Последующие проверки остановлены fail-fast и не считаются выполненными.

baseline-search-failure.json подтверждает такой же отказ на копии исходного HEAD без текущих правок. Диагноз и рекомендуемая отдельная задача — release-blocker.md. Ошибка относится к регистрации ресурса в старой тестовой fixture, а не к изменениям документации; поведение поиска и этот тест не изменялись. Дополнительно выполнены transition-recovery-final.json и work-state-final.json: PASS. Это целевые проверки, не замена полного успешного прогона.

multi-process-final.json: все 16 сценариев PASS, включая обязательный выбор из нескольких процессов, отказ для неразрешённого процесса, сохранение pin текущего Work, совместимость одного процесса и работу без Runtime. Публичный checksum inventory оставался неизменным во время полного прогона: SHA256 3752A77D9EA0AFF3247655CF6A44544C1DE7D34E4F4395C13D702A07446D789F.

## Границы

Парсерная проверка не исполняет 610 примеров; проверка ссылок не проверяет якоря, внешние URL или смысл всех документов. Исполнение подтверждено отдельно для batch fixture и Core update fixture. Чистая публичная копия без .pf — проверка переносимости нового теста, не релизная упаковка и не extracted archive qualification.

Версия/CHANGELOG, миграция именно 1.1.1, чистый release candidate, archive/extracted-test, тег, публикация и обновление установленного Core остаются отдельной работой. Текущая подготовка не выдаётся за разрешение на публичный выпуск.
