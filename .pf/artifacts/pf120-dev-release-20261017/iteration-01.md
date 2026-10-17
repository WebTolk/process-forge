# Итерация 1: constructor fixture и новый точный архив

2026-10-17. Первый полный source suite на 280e00d нашёл устаревшее точное ожидание списка параметров ProcessExecutionService в существующем smoke. Прогон продолжен для обнаружения всех ошибок; его FAIL сохраняется, старый ZIP 999667c5 не допускается к установке.

Отдельная test-only Work с непересекающейся областью завершена: report/closeout/handoff в pf120-dev-fixture-20261017, native run_completed, оба doctors exit 0. Исправлен только existing smoke guard: точный список прежних имён + optional work_metadata, KEYWORD_ONLY/None. Все 7 существующих тестов PASS; изменилась одна checksum entry. Новый source commit: 8ea152bfa6376a66fc87c7ed48d74eacc5c2ad41. Ни production bytes, ни CLI/MCP contracts не менялись.

Новая сборочная копия source-final и новый ZIP metadata-r2 не изменяют первый source worktree/логи/архив или sealed stage evidence. Обязательны native checksum/pack, точное сравнение двух ZIP (ожидаются только test file, inventory, generated Core manifest), закрытие обнаруженных source-suite failures и полный consumer suite нового ZIP до установки. Результаты source run будут указаны с исходной ошибкой и отдельным rerun; полный финальный архив должен пройти все consumer gates одним прогоном. Повтор идентичного всего source suite не заменит и не расширит эту проверку исполняемых байтов.

Лог и итоговый report должны явно различать первоначальный и финальный candidate. План install/restart и сохранения конфигурации прежний. Финальный exact archive hash и native apply будут записаны только после qualification; source 280e00d не будет выдаваться за новый installed commit.
