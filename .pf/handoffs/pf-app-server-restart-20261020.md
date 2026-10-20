# Handoff: App Server restart -> next user session

Objective: Перезапустить App Server после завершённой установки дев-релиза; сессию пользователь переподключает сам.

Current status: App Server штатно перезапущен из установленного Core; новый живой процесс, прежний завершился, health/readiness ready, интервал10 сохранён. Установленный source d6eb1412fb47ad21df50e4c446d0cc813589034e, повторного Core apply нет.

Input artifacts: .pf/artifacts/pf-app-server-restart-20261020/report.json; предшествующий .pf/handoffs/pf-python-quality-20261020.md сохраняет историческое состояние до этого отдельно разрешённого restart. Полные частные status/process receipts сохранены в .pf/tmp/pf-app-server-restart-20261020/.

Files changed: Только отчёт, журнал и этот checkpoint.

Files not to touch: Чужой dirty/staged слой, pending OOP54–55, завершённые/отменённые Work и их capsules. Следующий рефакторинг не запускался.

Known issues: Обычная попытка получила HTTP409 activity unknown; после предметной проверки выполнен явный операторский --force restart. Не утверждается полнота статистики активности. MCP до restart показывал stale при fresh source CLI; после переподключения нового хоста он ещё не проверен.

Required checks: В новой сессии сначала действительный подключённый pf.context и provenance загруженного Core/MCP. Старый snapshot ctx-20261020-072238-da5df2 был source fresh/ready до restart; не делать refresh только ради скрытия CLI/MCP расхождения. При сохраняющемся расхождении использовать отдельную будущую карточку pf-cli-mcp-context-consistency-20261019.

Next recommended action: Дождаться нового поручения после перезапуска сессии. Не повторять успешный Core apply, restart или проверки прошлого code cycle без нового основания. Этот checkpoint не является native continuation и не даёт новых разрешений.
