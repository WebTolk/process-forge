# Приёмка исходного результата

Дата: 2026-10-19. Результат: source accepted, pass_with_conditions.
Основания: reviewer/report.md (initial fail), reviewer-r1/report.md
(R1/P2 closed/pass, no new must-fix), original four worker reports,
primary-r1-tests/report.md и public-validation/report-v2.md.

## Review findings

Один независимый reviewer role проверил primary и все четыре вклада. Initial
R1 обнаружил необязательный write/flush до runtime.serve. Source revision 1 и
её fail report сохранены. Primary исправил только optional presentation IO
boundary, добавил постоянные проверки в отдельной test-only successor Work.
Отдельное corrective review подтвердило закрытие R1, неизменность прежних test
AST и propagation шести Runtime constructor/serve ошибок и двух mandatory-log
ошибок. Новых обязательных исправлений нет. Reviewer продукт не менял.

## Test plan / test cases / test report

План: общий TTY/non-TTY/None/encoding/version contract, explicit launch flag,
строгое own-window ownership, безопасные backends/отказы, Scheduler lifecycle,
HTTP/CLI/JSON/singleton сохранение и источник Core version. R1 добавляет реальные
write/flush ошибки header и diagnostics без потери serve результата.

Выполнение:

- Primary exact smoke_server_operator: 29 methods и прежние actual HTTP/guard/
  force/auth/owner/launcher/JSON checks PASS.
- Primary exact smoke_runtime_mcp_autostart: PASS; настоящих Scheduler команд нет.
- Primary unchanged smoke_runtime_singleton_orphan: PASS; fixtures изолированы.
- Independent reviewer 1: 27 console + 26 Linux mock checks PASS; reviewer 2:
  RED 12 cases на прежней функции только в памяти, GREEN 12 на текущей,
  29 console methods PASS, original probe исправлен; mandatory errors не скрыты.
- Обе public-copy revisions по 1395 файлов: schema/cleanliness/checksum PASS,
  все copy hashes проверены. Corrective delta — console.py, smoke suite и
  соответствующие две inventory записи. 17 final source hashes совпадают.
- Шесть EN/RU документов и 30 links/anchors проверены; future Textual/config
  flag не объявляются существующими. --console и CLI aliases сохранены.

Canonical operator/autostart independent reruns в worker sandbox остановились
до assertions на TemporaryDirectory WinError5; это не независимый PASS этих
двух запусков. Primary выполнил их без изменения тестов в доступном parent
окружении. Worker liveness ограничения также отделены от parent singleton PASS.

## Scope приёмки и handoff

Gate относится к source/dev результату этой Work. GUI successful acceptance,
installed Core, фактический Scheduler task и Runtime/connected-host обновление
в эту приёмку не входят и не заявляются. Native Windows proof — только
невидимый nonclassic HWND refusal; реальные classic/shared/X11 окна остаются
непроверенными. Linux GUI недоступен. Windows Terminal/Wayland unsupported cases
задокументированы. Архив/stable publication/установка не требовались.

Все source writers остановлены; две review revisions неизменяемы. Родительская
Work выполняет отдельный task commit и parallel push одного SHA в origin/dev
и gitverse/dev с readback. Остальные Work доставляют лишь свои artifact contributions.
До завершения readback root delivery не считается завершённой. Textual остаётся
следующим отдельным заданием, эта задача на нём не продолжается.
