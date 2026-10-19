# Исправление независимого finding R1

Дата: 2026-10-19. Статус: ready_for_review.
Исходный report reviewer/report.md с fail/P2 сохранён неизменным.

tools/pf_runtime/console.py теперь ограничивает обработку OSError/ValueError
областью необязательного консольного представления: header, flush и сообщение
о неподдерживаемой минимизации. Потеря/закрытие TTY прекращает только этот вывод.
runtime.serve остаётся за пределами catch в service.command_serve, возвращает
собственный результат; ошибки сервера и обязательных журналов не подавляются.
Если header не удалось вывести, до GUI-запроса управление не доходит.

Основной исполнитель в отдельной bounded successor Work добавил постоянные
regression cases в smoke_server_console.py. RED до исправления: 12 errors;
GREEN после: два новых methods/12 subcases, canonical operator 29 tests и
autostart/MCP entrypoint exit 0. Подробности primary-r1-tests/report.md.

Новый публичный freeze: public-validation/public-view-manifest-v2.json;
1395 файлов, от предыдущего inventory изменились только console.py и новый
regression suite; удаления/добавления отсутствуют. Штатные schema, cleanliness
и checksum validators новой копии прошли. Исходный checksum inventory обновлён
в области root primary. Предыдущие manifest/report/hash files не переписаны.

Вторая revision source hashes и отдельный reviewer-r1 report фиксируют повторную
проверку. Успешная реальная GUI-минимизация Windows classic/Linux X11, установленный
Core и реальная Task Scheduler задача не квалифицированы этим исправлением.
