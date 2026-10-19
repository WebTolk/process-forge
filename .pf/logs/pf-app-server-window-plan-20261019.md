# Планирование окна App Server

## 2026-10-19 09:19 +04:00 - primary agent / planner

Task: исследование и план по `pf-app-server-window-ux-20261019`, без кода.
Files changed: продуктовых нет; созданы только собственные плановые артефакты.
Artifacts changed: `pf-app-server-window-plan-20261019/control.md`, этот журнал;
PF создал scoped assignment, immutable capsule и Run штатным `pf.work.start`.
Templates used: отдельные шаблоны не выбраны капсулой; использованы требования
артефактов и logging/handoff из `.pf/AGENTS.md`.
Tools used: PF MCP context/actions/resolve/work-start/work-state; Serena;
существующие source/installed CLI для обновления и проверки контекста.
Decisions: подтвердить свежесть через подключённый MCP после установленного
CLI; создать отдельную planning-only Work вместо изменения legacy-капсулы;
работать одним агентом, поскольку capsule запрещает subagents.
Risks: первоначальная source/installed разница official process package
выявлена и разрешена без инфраструктурных действий; derived reports stale;
имеется большое чужое dirty/untracked состояние; исходный способ запуска окна
не подтверждён. Компоненты PF и monitor не запускались и не перезапускались.
Next steps: пройти intake; исследовать код и локальную документацию; подготовить
варианты, рекомендацию и приёмочные критерии; сохранить handoff.
Handoff: точные селекторы и checksum записаны в `control.md`.

## 2026-10-19 09:34 +04:00 - primary agent / planner

Task: исследование текущих путей запуска, выбор UI и проверка лицензирования.
Files changed: продуктовых нет; собственные документы и JSON evidence в
`pf-app-server-window-plan-20261019/`.
Artifacts changed: `research.md`, `domain.md`, `product-baseline.json`,
`device-observation.json`, `source-evidence.json`, `plan.md`, `license-note.md`,
`future-ideas.md`.
Templates used: pinned process artifact requirements; отдельные шаблоны
капсулой не выбраны.
Tools used: Serena symbols/patterns, PF Work search/resolve/transition,
read-only CIM/Task Scheduler, installed CLI help, локальные Python mirrors,
официальные сайты Textual/Click/Typer/Rich/Qt/Python/Microsoft/Apache.
Decisions: пользователь подтвердил logon-сценарий и выбрал Textual;
сервер и панель имеют независимый lifecycle; список проектов и подробности
сохранены только как будущая идея. MIT Textual совместима с заявленной
Apache-2.0 PF при сохранении уведомлений. Специального install-флага
минимизации нет; `--python pythonw.exe` означает отсутствие консоли,
не сворачивание. Основной план сохраняет исходное требование минимизации;
упрощённый режим без окна остаётся альтернативой.
Risks: точный владелец окна при logon не доказан; найденная scheduled task
уже использует pythonw, текущий сервер запущен иначе. Source и installed
`service.py` различаются, но `command_serve` одинаков. Ни это чтение, ни
версия 1.2.0 не являются runtime byte acceptance. Будущие dependency pins,
GUI startup acceptance и third-party inventory ещё не выполнены.
Next steps: проверить документы и хеши; закрыть только planning-only lifecycle;
сохранить handoff, исходный implementation backlog оставить открытым.
Handoff: продуктовая реализация, установка и автозапуск не выполнялись.

## 2026-10-19 09:38 +04:00 - primary agent / planner

Task: учесть окончательные уточнения пользователя по Windows/Linux и monitor.
Files changed: продуктовых нет.
Artifacts changed: `plan-v2.md`, незарегистрированные delivery/handoff и журнал.
Templates used: те же требования pinned PF-процесса.
Tools used: официальные источники механизмов окон; PF evidence остаётся native.
Decisions: сохранить уже зарегистрированную ревизию 1 неизменной; ревизия 2
закрепляет серверное окно свёрнутым, logo/версию при показе, общий launch
contract для Windows/Linux. Textual относится к отдельной будущей read-only
фиче monitor; предложено PFConfig.autostart_pf_app_server_monitor, default false,
плюс независимый ручной запуск/ярлык. Список проектов отложен дальше.
Risks: прежнее толкование «без окна» не является требованием пользователя;
pythonw не подменяет минимизацию. Platform mechanics и реальные GUI проверки
ещё должны быть выбраны/исполнены в будущей реализации.
Next steps: проверить ревизию 2, зарегистрировать её как актуальный план;
завершить только планирование.
Handoff: основной вход теперь `plan-v2.md`; ревизия 1 сохранена для истории.

## 2026-10-19 09:42 +04:00 - primary agent / planner

Task: итоговая проверка и фиксация планового результата.
Files changed: продуктовых нет; 1 232 tracked product/doc hashes совпадают.
Artifacts changed: `review.md`, `product-preservation.json`, актуальные
delivery/handoff; plan-v2 зарегистрирован штатным PF evidence.
Templates used: требования проверки/передачи pinned process.
Tools used: локальная проверка JSON/ссылок/хешей, PF context/work-state/transition,
Git только для собственных переносимых плановых Markdown материалов.
Decisions: context fresh, diagnostics пусты; исходная backlog assignment
по точным селекторам остаётся open/draft. Реализация и release/build/install
отмечены not_applicable. Независимая review и продуктовые тесты не заявляются.
Risks: проверки GUI/logon, dependency pins и root cause окна остаются
будущей продуктовой Work; это не остаточные правки кода текущего поручения.
Next steps: штатное завершение evolve и run-doctor; окончательное состояние
подтверждается native Work journal/readback. Продукт не начинать.
Handoff: `.pf/handoffs/pf-app-server-window-plan-20261019.md`.
