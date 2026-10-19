# PF App Server: серверное окно — результат задачи

Дата: 2026-10-19. Source implementation и integrated assurance завершены.
Независимое source review принимается с явно указанными GUI-ограничениями.
Фактический commit, оба remote readback и финальные doctors — в локальных
delivery-receipt.json и doctor-receipt.json рядом с этим отчётом; PF journal и
точная terminal Work являются актуальным состоянием доставки.

## Что изменилось

- .pf/AGENTS.md сохраняет режим 1-1-4: primary совмещает orchestration/execution,
  один независимый reviewer проверяет всех, четыре PF native workers с отдельными
  scopes; число workers можно увеличить. Координация и READ_ACK через PF,
  разрешённые знания Python PF использованы в плане, реализации и review.
- Foreground serve/run автоматически показывает PF logo, running Core version,
  PID и назначение на TTY. --console сохранён. Non-TTY/None stdout не получает
  header или GUI-вызовов; ASCII fallback без ANSI. Потеря write/flush выводит
  из optional presentation, а не из запуска Runtime.
- Общий --minimized запрашивает минимизацию только отдельного проверенного окна.
  Windows classic и Linux X11/xterm имеют узкие adapters с проверкой владения
  и наблюдением свёрнутого состояния. Shared terminal не сворачивается.
- Windows autostart profile прямо выполняет tools/processforge.py runtime serve
  --minimized с точным interpreter. Сохранено владение Task Scheduler процессом.
  EN/RU инструкции объясняют прямой запуск, ограничения и операторскую миграцию
  старого action через preview/--replace; настоящий task не менялся.
- Новые постоянные console checks встроены в canonical smoke_server_operator.
  HTTP/auth/guarded shutdown, singleton и MCP контракты сохранены.

## Команда и независимость

Primary интегрировал common console/parser/service/rules/inventory. Четыре
native worker contributions: Windows, Linux, EN/RU docs и regression assurance.
У всех отдельные exact Work/capsule, Agent Ledger session, READ_ACK/RESULT.
Один reviewer role проверил все пять вкладов и нашёл P2 R1 в primary-коде.
Первый fail report сохранён; primary исправил presentation и получил отдельный
test-only successor/handoff для permanent regression cases. Corrective revision
проверена независимо заново; код reviewer не писал.

## Проверки

- До R1 fix: новые 12 subcases воспроизвели отказ; после — прошли. Итоговый
  canonical operator: 29 console methods и actual HTTP guards/launcher/JSON PASS.
- Autostart/MCP canonical smoke PASS; неизменённый singleton/orphan/concurrency/
  publication smoke PASS в parent. Sandbox ACL/liveness limitations workers
  отделены от этих выполненных canonical результатов, assertions не ослаблялись.
- Frozen source revision 2: 17 task product/rule/inventory файлов. Public
  copy содержит 1395 файлов, с raw/release hashes. Public schema, cleanliness
  и checksum проверки PASS. .pf/process-forge.yaml взят из pre-task Git baseline;
  посторонний локальный dirty config сохранён.
- Два прежних stale checksum hashes приведены к уже committed bytes;
  исходники этих tools не менялись. source/global historical private findings
  не объявляются исправленными. Детали — public-validation/report-v2.md.

## Пределы и следующий шаг

Windows Terminal/ConPTY и Wayland/XWayland не имеют реализованного безопасного
механизма в этом slice; сервер остаётся работоспособным и сообщает ограничение.
Linux backend требует local X11, отдельный xterm -e, readable /proc, заранее
установленные xprop/xdotool. PF не устанавливает эти программы.
Успешная реальная minimization Windows classic/Linux X11 не подтверждена.
Native Windows fixture подтвердил лишь отказ при invisible/nonclassic HWND,
не квалифицировал видимую classic/shared console. Это source-only/dev результат,
не installed/Runtime/connected-host GUI acceptance.

Installed Core, Runtime/MCP и настоящая Task Scheduler task не обновлялись и не
перезапускались. Release ZIP/stable tag/channel/PR не публиковались.
Textual monitor, PFConfig.autostart_pf_app_server_monitor и project-list/detail
feature не реализованы: это следующие отдельные задачи. После этой задачи
работа останавливается; старые capsules, reports и посторонние файлы сохранены.
