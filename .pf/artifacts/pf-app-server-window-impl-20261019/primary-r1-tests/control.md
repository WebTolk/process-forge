# R1: постоянная проверка записи и flush TTY

Дата: 2026-10-19. Исполнитель primary, дополнительного native worker нет.
Work: garage-pf-app-server-r1-permanent-regression-coverage-20261019-primary-e.
Assignment: pf-app-server-r1-permanent-regression-coverage-20261019-primary-executor.
Capsule checksum: sha256:7817cfaa50232520977bfcb98d20def44287a504627ede949f574d9d978002ce.
Fresh/valid/ready. Scope product write: только tools/smoke_server_console.py;
остальные записи — собственные artifacts/tmp/log. Родительская primary Work
отдельно владеет исправлением console.py.

## Task record / context / lifecycle / scope

Независимое finding msg_89ce7a820c264cefa38a50f9e7eaea36: optional TTY header
write/flush OSError прерывает command_serve до RuntimeProcess.serve. Предыдущий
assurance worker завершён и прекратил изменения. Получен явный неизменяемый
handoff с exact predecessor/capsule; параллельного writer нет.
Первый scope input с uppercase output id отвергнут до создания Work; затем
использован поддерживаемый r1-test-report. Старые capsules не изменялись.

## Investigation / domain / architecture / implementation plan

Добавить два meaningful test cases в существующий canonical console suite:
реальные методы write и flush у TTY stream выбрасывают ожидаемые OSError/ValueError,
а вызов service.command_serve всё равно доходит до mocked RuntimeProcess.serve,
возвращает его результат и не выполняет GUI при недоступном выводе. Сохранить
существующие assertions всех остальных console/ownership checks.

До изменения продукта новые cases должны воспроизвести дефект. После узкой
обработки вывода в родительской Work — пройти. Исходный reviewer сначала
завершает и сохраняет revision 1; до этого 17 frozen files не меняем. Затем
создаём новые hashes/public-validation revision и отдельно отдаём R1 patch
независимому reviewer. Исторические report/manifest/hash files не переписываем.
Ни установки служб, ни реальных Scheduler/Runtime вызовов и новых features.
