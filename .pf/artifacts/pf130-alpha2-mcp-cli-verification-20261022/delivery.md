# Доставка проверки

Единица результата — report.md, evidence.json, plan.md, assurance.md, этот
delivery.md, evolution.md и отдельный журнал primary. Изменений продукта нет.
Проверенные операции MCP/CLI — PASS; ограничения перечислены в report.md.

Архивы, release channels, install и infrastructure delivery неприменимы:
пользователь поручил проверить уже установленный alpha2. Повторять прежнюю
поставку не требуется. Нативная PF Work используется для фиксации evidence и
последовательного закрытия проверки; предыдущая release Work остаётся terminal.

Документы фиксируются отдельным коммитом в dev. Точный SHA и readback origin/dev
и gitverse/dev фиксируются в native transition evidence после commit/push;
следующий этап не получает утверждения об успешной доставке до проверки refs.
Ранее существовавшие dirty/untracked файлы не включаются. Перед staging других
staged changes не было. Итоговые документы проверены на JSON, whitespace и
private paths; scoped staged diff проходит git diff --check.
