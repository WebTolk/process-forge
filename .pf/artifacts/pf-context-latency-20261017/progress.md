# Журнал диагностики pf.context

## 2026-10-17 — primary
Задача: объяснить14–15с pf.context. ПроанализированыMCP handler, ProjectContextService/composition иstate path; startupfresh, exactWork/capsulevalid/ready. ИнструментыPF MCP,Serena,узкие чтения.
Изменения: толькособственныеstageартефакты. Статус: план/анализ завершены, далее read-only installed handlerprofile. Риски: standalone cold cache/cProfileoverhead нужноотделитьот actualhost. Productfix,перезапуск,полныеsmoke иисторияне затронуты.

## 2026-10-17 — primary, результат
Подтверждены2полныхWorkобхода:9.403+6.632с из17.337с(92.484%). Livecacheprobe: повторныйвызов4sharedhits,2689parses/evictions;64MiBshared и8MiBrequest исчерпаны. cProfile43.538с — отдельныйинструментированныйзапуск,необычнаяlatency.
Сохраненыreport/publicsummary/phase/counter/profileevidence искрипты. Nativeэтапы доrun_completed; дальнейшаяпроверкаdoctors иdeliveryrecords. Остаток: исправлениеprojections/selection — отдельнаяWork, нерасширениеэтой. Product/runtime/история неизменны.

## 2026-10-17 — primary, закрытие
Exactreadbackrun_completed/completed/done иvalidcapsule; native task/run doctorsexit0. Продуктовыефайлы иисходныйstaging сохранены. Публикуются толькоown machine-neutral отчёты; rawpstats/полныйprofile искрипты retained локально. Следующийшагопределёнвhandoff, исправлениеещёнереализовано.
