# Handoff: installed context fix -> реальная проверка после restart

Objective: после пользовательского перезапуска проверить настоящий подключённый
MCP и CLI на одном проекте/снимке с уже установленным исправлением.

Current status: УСТАНОВЛЕНО. Прямое поручение «Установи и я перезапущу сессию»
выполнено. Native update core-update-20261020T124659Z, applied at 2026-10-20 12:46:59 UTC,
exit0, один apply --confirm без force. Новая установка не повторяет старый утренний
core-update-20261020T081547Z. Не применять пакет снова и не запускать refresh.

Установленный dev source: 526c5d13e42e96693802760cce35fe896e208708, продуктовая
версия 1.2.0. Archive SHA:
acaa0ff8b3b8a368520a7a115e3db14efe45c74555425f74ea116d9dd9b36457.
Пять заменённых files: project/source_check.py, project/snapshot_sources.py,
EN/RU docs/concepts/context-resolution.md, checksums/processforge.sha256.
1458 managed hashes/size и 5 backup preimages PASS; old manifest JSON values PASS.
Backup: configured installed Core/runtime/core-update/backups/core-update-20261020T124659Z.
Status installed, incomplete_update=false; repair nothing_to_repair.
Native automatic doctor-workplace: PASS, 197 PASS lines.
7 protected, 243 Workplace YAML, 69 static unowned Core и 8 чужих source guards сохранены.

Completed delivery identity (НЕ RESUME):
- run: garage-pf-context-device-install-20261020-operator-explicitly-requested
- assignment: pf-context-device-install-20261020-operator-explicitly-requested-install
- context: pf-context-device-install-20261020-operator-explicitly-requested-install-capsule
- capsule: a2a82c892841bbee205732535c27fa262859017882453228f385686343a3f7cb
Native run_completed/completed/done, incomplete []; run-doctor PASS.

Input artifacts: .pf/artifacts/pf-context-device-install-20261020/identity.json,
apply.json, installed-verification.json, context-parity-after-install.json,
delivery.md, lifecycle/evolve.json, run-doctor.json. Raw native evidence,
before manifests, guards и module provenance — в собственном
.pf/tmp/pf-context-device-install-20261020, сохранены как installation evidence.

Known issues: установленный CLI и source CLI теперь оба fresh/fresh/ready/continue
со stale_resources [] на исходном ctx-20261020-072238-da5df2 и неизменном SHA
bd7dc7f033fe9f95f4c6903ea168868251db7666ef536c12479f7bcae667a05a.
Текущий connected pf.context после установки всё ещё stale/ask_operator: код уже
на диске, но этот host не перезапускался. Runtime/MCP/host hooks/Ledger не трогались.
Зафиксированные процессы-кандидаты MCP/Runtime стартовали до apply; не выбирать
новейший PID как доказательство реального соединения.

Required checks: в новой сессии сначала прочитать живой .pf/AGENTS.md и этот handoff,
вызвать настоящий pf.context для project root, проверить host/process/module-root
provenance после apply и получить свежий installed CLI project-context-check на
том же snapshot. Сопоставить context/resource/execution readiness, policy/reasons.
Не подменять connected-host proof отдельным stdio или in-process adapter.
Если host сохранил прежний процесс/код, требуется реальное переподключение MCP,
а не повтор установки. Если snapshot реально изменился, исследовать точную причину;
не маскировать результат очередным refresh.

Files not to touch: чужой dirty/staged слой и OOP54-55; их рабочие файлы сохранены.
Историческая planning-only карточка pf-cli-mcp-context-consistency-20261019 пока
open: source и device delivery приняты, actual connected-host критерий остаётся.
Не resume terminal source или delivery run и не расширять их capsules.

Next recommended action: реальное connected MCP/CLI сравнение после пользовательского
restart; read-only orientation не требует новой Work. Если нужно записать дальнейшие
артефакты/закрыть критерий, оформить новую узкую verification Work по живому контексту.
Будущая 1.3.0-alpha1 ещё не выпущена; прежние два препятствия alpha остаются в
.pf/artifacts/pf-context-parity-20261020/primary/alpha-preparation-handoff.md.
Содержимое ZIP не проверять и archive-test не запускать по указанию пользователя.
