# T08 — план приёмки после перезапуска

Дата: 2026-09-25. Продолжается существующая Work со стадии code-assurance.

1. Снять реальные MCP context/state и сравнить source/installed CLI, snapshot,
   process pin и разрешённые ресурсы. Проверить identity нового процесса.
2. Проверить search/resolve и отказ доступа. Пустая выдача главного проекта
   диагностируется отдельно от свежести snapshot и исправности транспорта.
3. Создать только локальный fixture `.pf/tmp/t08-host-acceptance-20260925/`.
   Использовать существующий Workplace без изменения его конфигурации/хуков.
   Fixture имеет собственный process с обязательными artifact/gate evidence;
   через подключённый MCP пройти start/state/transition/completion.
   Между стадиями новая stdio-связь с installed Core должна продолжить ту же Work.
4. Session-bound положительные/отрицательные сценарии — в изолированном
   Workplace существующих регрессий; чужие реальные Ledger sessions не использовать.
   Проверить missing_session и неподходящий ресурс через подключённый MCP.
5. Сохранить точные ответы, review и test report; закрыть assurance, delivery,
   evolve через текущий MCP. Не изменять уже зарегистрированные evidence.
6. Обновить handoff. T01 остаётся отдельной Work согласно плану r02.

Source остаётся a180ad624442d4fbe8ac1710073ef7d4c44babc4. Новый product patch
не планируется. Координация single_agent; subagents запрещены процессом.
Serena/IDE MCP в текущем наборе инструментов отсутствуют; используется узкий
UTF-8 shell fallback. Применимых skills/Python toolchain в D:/.agents не найдено.
