# Выводы по задаче серверного окна

Дата: 2026-10-19. Применение ограничено этой задачей; новых задач не запускает.

Режим 1-1-4 закреплён в .pf/AGENTS.md. Действительные четыре worker contributions
и отдельный независимый reviewer проверены через PF reports/chat/READ_ACK и
Agent Ledger. Primary сохранил исполнение общей части и интеграцию. Все области
записи разделялись; R1 tests переданы primary новым exact successor/handoff
после завершения прежнего test writer. Рост числа workers допустим по потребности.

Независимость review дала измеримый результат: R1 в primary обнаружен после
изначальных 27 checks, воспроизведён на реальной command_serve цепочке и исправлен
до commit. Постоянные write/flush cases увеличили console suite до 29 methods.
Optional UI IO не должно владеть серверным lifecycle; mandatory Runtime/log
ошибки должны сохраняться, что повторный reviewer проверил отдельно.

Фиксировать источник evidence: mock PASS, native refusal, parent canonical PASS,
public-copy/hash parity и real GUI acceptance — разные утверждения. Исправленный
source не означает обновлённый installed Core или реальную Scheduler task.
Открытые GUI-проверки перед будущей платформенной квалификацией: visible Windows
classic (own/shared), Linux X11/xterm; Windows Terminal/Wayland limitation остаётся.

Практика PF: driver без configured model может завершиться до работы — это не
worker contribution. Output ids должны быть допустимыми lowercase ids. После
неясного transition ответа сначала exact state/readback, затем только нужное
продолжение; не редактировать капсулы. Не менять private dirty config ради public
validators: использовать объявленную tracked baseline конфигурацию и proof hashes.

Future Textual monitor с отдельным autostart_pf_app_server_monitor и позднейшим
списком проектов остаётся в plan-v2/future-ideas. Сейчас не добавлять зависимость,
настройку, UI или installer. Следующая задача определяется отдельным поручением
пользователя. Эта задача завершается source commit, одинаковым dual remote SHA,
PF terminal states и точными doctors; службы устройства не перезапускаются.
