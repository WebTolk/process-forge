# Диагностика стоимости pf.context

Поручение: объяснить измеренные14.675с конкретными этапами/функциями. Artifact-only Work valid/ready; source40581f2, installedd5947ea. Одинprimary, subagents=false. Никаких исправлений продукта/служб/истории.

План: точный MCP handler+Core owners; воспроизвести тот же read-only handler установленного Core в отдельном диагностическом процессе; прогрев, wall фаз иcProfile с callers/counts; сопоставить с фактическим MCP14–15с; сохранить профиль икраткий отчёт с границами будущего исправления. Точечные workload timings достаточны, tests/install/restart не нужны.
