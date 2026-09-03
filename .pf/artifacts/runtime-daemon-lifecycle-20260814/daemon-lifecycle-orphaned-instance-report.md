# Защита orphaned live Runtime instance

Status: done

Независимый review нашёл корректный edge case: потеря `runtime.lock` при живом daemon и сохранённом `service.json` не должна означать, что workplace свободен.

`inspect_lifecycle()` теперь классифицирует живой service state с `instance_id`, но без matching lock, как `orphaned`. `runtime start` отказывает с явным требованием stop/recovery, не создавая второй daemon. `runtime stop` использует только проверенный `/readyz` endpoint для graceful shutdown orphaned instance; без такого endpoint он отказывает, а не завершает PID, принадлежность которого lock уже не подтверждает.

Smoke удаляет lock у живого daemon, доказывает отказ второго start, затем штатно останавливает orphaned instance и успешно запускает новый.

Проверки: `py_compile`, `smoke_long_lived_runtime.py`, `smoke_runtime_host_poc.py`, schema validation и `git diff --check` — pass.
