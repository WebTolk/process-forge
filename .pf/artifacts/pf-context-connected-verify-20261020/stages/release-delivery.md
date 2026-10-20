# Доставка документальной приёмки

delivery-report: evidence/report PASS, historical task done штатной командой;
native task/run doctors PASS, snapshot и постороннее содержимое run сохранены.
Текущая Work доставляется отдельным Git коммитом после native terminal, затем
обе ветки dev читаются обратно. Exact SHA и транспортные результаты сохраняются
в собственном .pf/tmp/pf-context-connected-verify-20261020/git-delivery.json.
Общий index сохраняет посторонние entries; shared файлы коммитятся трёхсторонним
применением только собственного native delta поверх HEAD.

release-readiness-decided: готова только эта документальная задача; альфа
остаётся отдельным неподготовленным кандидатом. Product release не выполняется.
delivery-profile-run-or-skipped-with-reason: source/ZIP release suites не нужны
для задачи без продуктовых изменений; archive-test прямо исключён оператором.
Требуется Git delivery, без установки, служб или публикации alpha/stable.

Handoff: evolve зафиксирует выводы и сохранение raw evidence; затем отдельный commit.
