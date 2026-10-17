# Handoff: test-maintainer -> dev-release

Objective: исправить ожидание существующего constructor smoke после одобренной Work metadata dependency.
Current status: семь существующих тестов PASS; syntax/diff/inventory delta PASS; native terminal/doctors и commit/readback фиксируются отдельными receipts.
Input artifacts: .pf/artifacts/pf120-dev-fixture-20261017/plan.md и report.md, родительская ошибка полного source suite.
Files changed: tools/smoke_work_transition_commit_service.py; одна строка checksums/processforge.sha256.
Files not to touch: исходный immutable source worktree и первый архив родителя; product files; history/config; immutable capsules/evidence.
Known issues: старый 280e00d suite сохраняет исходный FAIL и не должен выдаваться за полный PASS. В новом source исправлен только test contract; production payload прежний.
Required checks: родитель собирает новый чистый archive, проверяет checksum и полную consumer suite, затем выполняет разрешённые install/restart и системную приёмку.
Next recommended action: использовать точный delivered fixture commit; прежний ZIP 999667c5 не устанавливать.
