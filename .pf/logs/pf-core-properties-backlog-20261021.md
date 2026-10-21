# Регистрация будущей задачи общих свойств Core

## 2026-10-21 — task-registration-executor

Task: сохранить требование пользователя о доступе сервисов к свойствам ООП-ядра.
Files analyzed: точные committed tools/processforge.py, pf_runtime/monitor.py,
pf_runtime/service.py, common/release_identity.py, VERSION; существующие карточки.
Files changed: spec, evidence, validation/registration, handoff, этот лог и
нативные записи новой draft/open planning-only карточки.
Tools used: fresh pf.context, PF action contracts, Serena, native run-create,
task-create, run-summary, task-doctor, run-doctor, Git committed-source reads.
Decisions: общий объектный контракт; без дублирующих release-констант;
installed/loaded identity отдельно от protocol/spec; без запуска реализации.
Status: Task open, Run draft, writer=false; doctors exit 0 (12/18 PASS).
Risks: два ожидаемых WARN о будущем отчёте; архитектура API ещё не выбрана,
исторические константы протокола и immutable версии нельзя заменять номером релиза.
Next steps: изолированный commit/push карточки в оба dev remote, readback SHA,
затем остановиться. GitVerse использует существующий токен без раскрытия.
Handoff: отдельное разрешение и scoped Work нужны для будущей реализации.
