# Основания плана

- status: draft
- date: 2026-09-25
- source_commit: a180ad624442d4fbe8ac1710073ef7d4c44babc4
- purpose: сохранить подтверждённые выводы предшествующей сверки как вход плана

## Подтверждённые соответствия

Процессное ядро выполняет декларативный жизненный цикл без обязательной
модели, Ledger-сессии, hooks или daemon. Run и Assignment сохраняют стадии,
результаты и evidence; процесс закрепляется в Work. Драйвер по умолчанию —
manual; generic-shell даёт общий путь запуска внешнего исполнителя.
RawIngressKernel принимает provider/adapter как данные и сохраняет raw-событие
до производных эффектов.

## Выводы и привязка к задачам

| Вывод | Доказательство | Задачи |
|---|---|---|
| Чтение ресурсов не привязано к контексту активной Work | process_execution.py:_process_pin/_selected_resource_ids сохраняют ресурсы; garage.py:ResourceSearchService.search/ResourceResolveService.resolve читают текущий project snapshot | T01, T02 |
| Два пути построения капсул имеют разную полноту | ProcessExecutionService._write_capsule и tools/processforge.py:command_assignment_capsule | T01, T03 |
| Правила происхождения диалогов провайдеров находятся в общем Host | tools/pf_runtime/host.py:_allowed_conversation_message содержит codex-hooks и pf-codex-exec-worker | T01, T04 |
| Знания требуют от worker самостоятельной MCP-навигации | tools/processforge.py:render_worker_launch_prompt при knowledge grants предписывает остановку без MCP | T05 |
| Фильтрация сохранённого чата не является фильтром передачи модели | tools/processforge.py:redact_chat_content; tools/codex_exec_worker.py:prompt_payload/main передают payload CLI | T07 |

## Воспроизведения предыдущей сверки

1. Во временном проекте через реальные CLI/MCP зарегистрированы ресурсы A и B;
   выбран A, создана Work; проектный выбор заменён на B и обновлён snapshot.
   В work.state остался A, resolve(A) вернул denied, resolve(B) — available,
   поиск по уникальному тексту B вернул B. Это расхождение воспроизводимости
   контекста Work; выхода за текущую авторизацию проекта не показано.
2. В созданной Work capsule отсутствовали scope, outputs, workspace_access,
   resolved_resources и capabilities; context.required_sources был пуст.
   Это относится именно к пути pf.work.start, а не ко всем капсулам PF.
3. Прямой вызов Host provenance policy принял предусмотренное сообщение Codex,
   но отверг аналогичные сообщения другого/локального адаптера. Это узкая
   проверка функции; сквозная интеграция реальной другой модели не выполнялась.
4. Проверка общего worker-промпта с knowledge grant подтвердила обязательную
   MCP-навигацию и требование остановки при недоступном MCP.

Следующие тесты были успешно выполнены в ходе сверки:

- tools/smoke_garage_no_hooks_sessionless.py
- tools/smoke_multi_process_work_capsule.py — 16 проверок
- tools/smoke_work_transition_snapshot_pinned_process.py
- tools/smoke_central_event_ingress_kernel.py

Сырые выводы проверок находятся в текущем диалоге; это их сводка, не новый
запуск и не отчёт полной релизной квалификации. Регрессии для выявленных
расхождений требуется оформить в T02–T05.

## Исходное препятствие оформлению Work

При подготовке плана живой pf.context вернул stale для снимка
ctx-20260923-161416-01a377. Разрешённым процессом объявлен только
task-batch-execution, хотя оператор выбрал software-feature-development.
pf.work.start с выбранным процессом и целью подготовки плана вернул
action: blocked, reason: snapshot_not_fresh. Run и assignment не созданы.

На этом исходном этапе были сохранены только draft-документы плана, лог и
handoff. Они ещё не являлись свидетельством прохождения governance gates.
Существующие незакоммиченные файлы и исторические назначения не исправлялись.

## Обновление после указания оператора

Оператор затем явно поручил обновить контекст и работать через PF.
В .pf/process-forge.yaml добавлен выбранный process: software-feature-development;
существующий каталог processes сохранён. Source CLI project-context-refresh
завершился успешно; project-context-check подтвердил fresh и ready для
ctx-20260925-132122-444ce0. Созданы отдельные run и assignment:

- run: garage-review-and-deliver-the-pf-vision-alignment-work-plan-from-the-202
- assignment: review-and-deliver-the-pf-vision-alignment-work-plan-from-the-2026-09-25

Текущая Work ограничена проверкой и передачей плана. Её стадии проходят
обычными work-state/work-transition с evidence. Это не реализация T01–T07.
Подключённый MCP продолжал возвращать старый snapshot; использован PF CLI
из исходников проекта, без перезапуска или ремонта Runtime/MCP/Ledger.
Закреплённый снимок этой Work не переписывается при дальнейших обновлениях
контекста проекта. После завершения документов требуется финальная проверка свежести.

Serena при исходной сверке не извлекала Python-символы: Active languages: [].
Использованы прямое чтение UTF-8, точечный поиск, вызовы функций и временные
CLI/MCP fixtures. Общее видение в reference-projection читается корректно
как UTF-8; прежнее наблюдение о повреждении файла не подтвердилось.
