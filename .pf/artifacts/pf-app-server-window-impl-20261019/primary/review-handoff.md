# Передача независимому reviewer: серверное окно PF App Server

Дата: 2026-10-19. Требуется независимый обзор всех пяти вкладов, включая primary.
Реализация завершена, продуктовые writers остановили изменения. Reviewer не
изменяет продукт и не заменяется самопроверкой primary.

## Результат и границы

Единый --minimized запрашивает минимизацию проверенного отдельного серверного
окна. Автоматический TTY header содержит PF logo, Core version и PID.
Task Scheduler запускает прямо tools/processforge.py runtime serve --minimized,
с точным заданным interpreter и прежним foreground lifecycle. Windows classic
и узкий Linux X11/xterm механизм проверяют владельца и наблюдают состояние.
Windows Terminal/ConPTY, Wayland/XWayland и неоднозначность дают ограничение;
не затрагиваются shared terminal, SSH/headless. Никаких Textual/config monitor
feature, новых зависимостей и обновлений/перезапусков установленного устройства.

## Все вклады

1. Primary: .pf/AGENTS.md (1-1-4), tools/pf_runtime/console.py, service.py,
   tools/pf_cli/parsers/runtime.py, checksum inventory; orchestration, Python
   guidance, domain/architecture и integration/public validation evidence.
2. Windows worker: windows_console.py и windows_autostart.py; windows/report.md,
   changed-files.md, change-summary.md, verification.md.
3. Linux worker: linux_console.py; linux/report.md и checks.md, 26 mocked checks.
4. Docs worker: шесть EN/RU runtime-autostart/installation/runtime-monitor
   документов; docs/report.md, changed-files.md и change-summary.md.
5. Assurance worker: smoke_server_console.py, smoke_server_operator.py,
   smoke_runtime_mcp_autostart.py; assurance/report.md, verification.json,
   changed-files.md и change-summary.md. Финальный expected report поступает
   через native capture; дождаться его до финального вердикта.

Четыре native codex-exec worker имеют отдельные PF Works и Agent Ledger sessions,
READ_ACK/RESULT в общем PF chat. Они не делегировали, не коммитили и не публиковали.
Точные identities доступны в task artifacts/assignments; перепроверить scope и
hashes вместо доверия общему сообщению. Капсулы не переписывались.

## Проверки для оценки reviewer

primary/focused-checks-final.md: exact canonical parent commands прошли —
27 новых console checks, прежние actual HTTP guards/launcher/JSON, autostart/MCP,
singleton live-orphan/concurrent start и publication/failure cleanup. Новый suite
вызывается из canonical smoke_server_operator; монолит не менялся.
Worker TempDirectory ACL и child-liveness ограничения не повторились в parent;
тестовые assertions/продукт не ослаблялись. Parent suite повторён только после
финального delta 25 -> 27 и для выяснения сигнала singleton.

public-validation/report.md и public-view-manifest.json: 1395 public source
файлов, byte/hash parity; .pf/process-forge.yaml из pre-task Git HEAD вместо
постороннего dirty override. Public schemas, cleanliness и checksum PASS.
Source global scanners всё ещё имеют независимые historical/private findings,
они не исправлялись. Inventory: 4 new + 12 changed task paths, дополнительно
два старых hashes приведены к уже committed bytes; соответствие baseline
доказано preexisting-inventory-drift.json. Исходники этих двух tools не менялись.

Windows native CREATE_NEW_CONSOLE пробы доказали лишь безопасный отказ при
invisible/nonclassic HWND (1/2 clients, exit 0). Успешная minimization реальной
Windows classic console и Linux X11 **не подтверждена**; Linux GUI недоступен.
Это material limits, не full acceptance. Установленный Core не обновлён.

## Ремит независимого обзора

Проверить actual diff/новые файлы всех пяти авторов, UI/TTY/None/encoding,
loaded Core version, lazy IO, native ownership/races/timeout, Scheduler lifecycle
и сохранение exact interpreter, Linux refusals, полезность/интеграцию проверок,
EN/RU examples/links и будущие features, 1-1-4 rules и методику public validation.
Не ограничиваться совпадением hashes. Результат с severity, точными file/line
и reproducer для дефектов; distinguish must-fix vs platform acceptance limits.
Через PF chat отправить READ_ACK, findings и финальный вердикт; reviewer code
не пишет. Commit/push остаются primary после исправлений и принятого обзора.
