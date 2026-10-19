# PF App Server: серверное окно, команда 1-1-4

Дата: 2026-10-19. Владелец: pf-app-server-window-primary.

## Task record

Реализовать первую задачу из plan-v2: серверное окно запускается свёрнутым
при поддерживаемом запуске в графическом окружении; видимая консоль показывает
логотип PF, версию работающего Core и назначение процесса. Монитор Textual,
PFConfig.autostart_pf_app_server_monitor и список проектов остаются следующими
задачами. Закрепить определение 1-1-4 в .pf/AGENTS.md.

## Execution context summary

Свежий контекст ctx-20261019-051448-f6dad2; policy continue, diagnostics пусты.
Новая Work: garage-pf-app-server-server-window-implementation-20261019-implement-app.
Assignment: pf-app-server-server-window-implementation-20261019-implement-approved-f.
Capsule: pf-app-server-server-window-implementation-20261019-implement-approved-f-capsule;
checksum sha256:7fbc11b50cb4bdbc6304adf476707f7011d9b1ed45eb64eccf0d7a761f048875.
Действия read/write_artifact/write_product, readiness ready. Planning Work завершена
и не возобновляется. Историческая backlog Work остаётся неизменной.

## Lifecycle mode decision

software-feature-development@1.2.0, девять стадий. Команда: основной агент —
оркестратор и исполнитель; четыре нативных PF shell-воркера с отдельными
ограниченными Work; затем один независимый ревьювер всех пяти вкладов.
Каждый shell-воркер не вызывает собственных subagents. Режим допускает больше
воркеров, если появятся независимые обязанности. У каждого свой Agent Ledger
check-in и heartbeat. Общий PF chat: session, созданная Agent Ledger для
pf-app-server-window-primary; READ_ACK отличаем от автоматического capture.

## Разделение ответственности

| Участник | Область записи | Результат |
| --- | --- | --- |
| primary | .pf/AGENTS.md, tools/pf_runtime/service.py, console.py, tools/pf_cli/parsers/runtime.py, bin/pf-server.py; собственные артефакты | общая политика, заголовок и интеграция |
| worker-windows | tools/pf_runtime/windows_console.py, windows_autostart.py; собственные артефакты | Windows адаптер и профиль автозапуска |
| worker-linux | tools/pf_runtime/linux_console.py; собственные артефакты | Linux адаптер, явные границы X11/Wayland/SSH |
| worker-docs | docs/getting-started/server-operator.md, docs/ru/getting-started/server-operator.md, runtime-autostart.md в обеих локалях; собственные артефакты | инструкция установки и запуска |
| worker-assurance | tools/smoke_server_operator.py, smoke_runtime_autostart.py, smoke_server_console.py; собственные артефакты | точечные проверки после реализации |
| reviewer | только собственные артефакты | независимый обзор всех вкладов и подтверждение исправлений |

Уточняем существующие пути перед созданием scopes. Воркеры не коммитят и не
публикуют; интегратор делает один task commit и параллельный push того же SHA
в origin/dev и gitverse/dev. Чужие dirty/staged файлы сохраняем.

## Порядок и приёмка

Сначала scope, исследование, доменные правила и архитектурный контракт адаптеров.
Затем реализация primary/Windows/Linux и инструкция; после окончания кода —
worker-assurance и независимый reviewer. Проверяем TTY/non-TTY/None streams,
ASCII/UTF-8, версию Core, aliases, единственность сервера, пути с пробелами,
целевое собственное окно и отсутствие GUI-действий для SSH/headless.
Минимизация не подменяется pythonw/CREATE_NO_WINDOW. Не сворачиваем чужой terminal.
Неподдерживаемая GUI-возможность не должна мешать запуску сервера и должна быть
описана. Реальные Windows/Linux проверки отделяем от unit/mocked доказательств.
Без установки обновления на устройство и без перезапуска работающих Runtime/MCP.
Остановка после этой задачи; Textual следующим отдельным поручением.
