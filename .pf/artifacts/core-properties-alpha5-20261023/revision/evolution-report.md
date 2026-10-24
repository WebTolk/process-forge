# Evolve R03 / alpha5: кандидаты для будущей работы

Статус: capture/planning_only, узкая область проекта ProcessForge. Правила,
публичные API, hooks и global skills автоматически не изменяются. Это кандидаты
для отдельного исследования/решения и последующего bounded Work; не новые
обязательные release gates и не утверждение готовности широких OOP эпиков.

| Кандидат | Target и applicability | Основание и будущая проверка |
| --- | --- | --- |
| Убрать избыточное обязательное session_id при доказанной host binding | project_rule; PF MCP с достоверными host/hook facts | Прямое замечание пользователя. Хуки знают настоящий thread, но sessionless session_context вернул missing_session. Исследовать automatic discovery только при однозначной подтверждённой связи host/thread/Work; explicit selector сохраняется при ambiguity. |
| Согласовать бюджет полного archive profile с реальным полным source profile | delivery_profile; полный native PF archive suite на Windows | Default outer1200s недостаточен при измеренном source2231.51s. В этой задаче использован существующий native timeout-scale3, без смены тестов/guards. Будущее решение должно быть bounded и документированным, не бесконечным автоувеличением времени. |
| Сохранять раздельные raw streams и детали неуспешных nested smokes | delivery_profile; native QA helpers и archive runner | Первый source negative JSON получил лишние combined-stream bytes, которых старый helper не сохранил; archive tail также не сохранил подробности smoke на общем тайм-ауте. R2 прошёл полный профиль за3340.69s с FAIL, но штатная очистка удалила nested report и детали более раннего отказа. Нужны точные stdout/stderr/exit/timeout receipts до JSON parsing и сохраняемый nested report. Не фильтровать ошибки ради PASS. |
| Проверять configured model до native worker launch | project_rule; реальные PF Codex shell profiles | Первая финальная review attempt завершилась до Codex: model not configured, unknown_exit. Явная модель в новой попытке дала настоящую hook session, durable result и независимое ревью. Не выдавать accounting session за proof execution. |
| Проверять observer через настоящий Windows launcher boundary | delivery_profile; диагностические archive collectors | В R3 фактический native entrypoint и полный extracted profile прошли с exit0, но private collector вернул1: profiler остался в bin/pf.py shim и не проследовал через os.spawnv. Будущий selfcheck должен покрывать делегирование в subprocess, отдельно сохранять native/collector exit и nested report. Текущий collector failure сохранён, nested count не придуман. |
| Сделать полную worker coverage доступной при штатной process acceptance | project_rule; наблюдение и guarded Runtime lifecycle | После alpha5 apply normal restart отказал409 при partial/budget coverage и running=null. Это отдельный будущий анализ наблюдения, не разрешение менять guard/бюджеты или считать observed0 полным idle. Actual Runtime и connected MCP остаются отдельными gate. |
| Закрепить практику проверки owning service на настоящих consumer seams | knowledge_package; PF Python/OOP migration | Первое независимое ревью нашло CP-A5-R01: owner знал build, а Runtime/MCP теряли его смысл. Исправление и постоянные тесты проверяют loaded A/installed B с одинаковой version label через actual service/doctor/action provenance, fresh boot и unknown remote identity. |

Для session discovery будущая приёмка должна включать два окна/агента, stale,
checked-out и restarted sessions, cross-project и cross-Work access, отсутствие
impersonation, current authorization/revocation, отличие capture от READ_ACK и
предсказуемый explicit-selector fallback. Нельзя выбирать newest/first session
или общую project Work projection как подтверждение связи. Реальные hook thread
и virtual accounting session — разные сущности. Это продолжает сохранённый
`primary/evolve-session-discovery.md`, а не внедряет обход текущего binding.

Сохранённые отрицательные результаты: исходное CODE NO-GO на b2dc2ec0, первая
неконфигурированная review attempt, первый source full failure и первый archive
timeout. Последующее GO относится только к проверенному исправленному source
af68fecf и конкретным настоящим повторным receipts; история не переписывается.
Отдельно сохранён и нативно закрыт disclosed generated-receipt remediation.

Финальный native source прошёл274/274. Archive R2 завершился полным FAIL за3340.69s;
archive R3 завершился настоящим native PASS/exit0 за3453.345s wrapper time,
при отдельном collector failure1. Installed-copy858/7/383 и8 native smokes прошли.
Это конкретные новые receipts, которые сохраняют прежнюю историю отказов.

При реализации любого кандидата снова прочитать исходные specs/ADR/domain/
direction/migration contract, получить отдельный narrow scope и current PF
context, использовать PF Python knowledge и прежние owners. Не превращать
эти наблюдения в разрешение на инфраструктурный ремонт или новый framework.
