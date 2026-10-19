# Handoff: primary planner -> следующая Work по App Server

Objective: спланировать устранение пустого серверного окна и Textual-панель,
сохранив запрет на реализацию в текущем поручении.

Current status: план подготовлен для review. Проверяемые результаты и точные
селекторы содержатся в материалах ниже; окончательное native состояние
читается через `pf.work.state` с этими селекторами.

Run: `garage-pf-app-server-window-planning-20261019-planning-only-scoped-succe`.
Assignment: `pf-app-server-window-planning-20261019-planning-only-scoped-successor-fo`.
Context: `pf-app-server-window-planning-20261019-planning-only-scoped-successor-fo-capsule`.
Capsule checksum: `sha256:e040a5a63dae90034e25233a907392f897879b68981a2f1c22c671eed5389625`.
Snapshot: `ctx-20261019-051448-f6dad2`.

Input artifacts:

- `.pf/artifacts/pf-app-server-window-plan-20261019/plan-v2.md` — основной план;
- `research.md`, `domain.md`, `control.md` в том же каталоге — факты и границы;
- `license-note.md` — MIT Textual и заявленная Apache-2.0 PF;
- `future-ideas.md` — список проектов/подробностей, только на будущее;
- `source-evidence.json`, `device-observation.json`, `product-baseline.json`,
  `product-preservation.json`, `review.md` — наблюдения и проверка планирования.

Files changed: только собственные плановые артефакты, журнал и этот handoff;
PF штатно обновлял свои lifecycle records и свежесть контекста.

Files not to touch: чужое dirty/staged/untracked состояние; immutable capsules;
исходная legacy-карточка `pf-app-server-window-ux-20261019` и её история;
текущие OOP slices вне будущего явно назначенного scope.

Known issues: пользователь подтвердил появление окна при Windows logon,
но владелец окна не доказан. Scheduled action уже использует pythonw;
наблюдавшийся сервер запущен под python иначе. Само повторение установки
не является доказанным исправлением. Source/installed service.py отличаются;
дисковые совпадения отдельных символов не квалифицируют загруженный процесс.

Required checks: перед кодом свежий pf.context, новая scoped Work и актуальные
architecture/source pins; при реализации — identity/lifecycle/stop guards,
терминальная приёмка и отдельная фактическая GUI/logon проверка. Textual должен
импортироваться только UI-адаптером. Dependency lock и лицензии проверяются
на конкретной поставке. Исходный monitor остаётся read-only.

Next recommended action: прочитать ревизию 2 и принять отдельное поручение
на серверное окно: свёрнутый GUI-запуск на Windows/Linux, логотип/версия
в видимой консоли, проверка достаточности настроек установки. Textual-монитор
выделен в отдельную будущую фичу: read-only TUI, запуск вручную/по ярлыку
либо по PFConfig.autostart_pf_app_server_monitor (предлагаемый default false).
Закрытие монитора не останавливает сервер. Список проектов — ещё более
поздняя идея. pythonw не является согласованной заменой минимизации.

Ни handoff, ни завершение planning lifecycle не разрешают устройство,
инфраструктурные действия, установку, публикацию или расширение капсулы.
