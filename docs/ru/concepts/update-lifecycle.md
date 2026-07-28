# Update lifecycle

Цикл обновления явный и управляется оператором:

1. `update entity-sources rebuild` собирает update sites из manifest-ов, installed subjects, registries и overrides.
2. `update candidates refresh` читает manifests, сравнивает версии и пишет `runtime/update/candidates.json`.
3. `update notifications list` показывает уведомления; Director inbox опционален.
4. `update changelog show` показывает URL changelog и локальное содержимое для file-provider.
5. `update stage` копирует artifact в `runtime/update/staged/<candidate-id>/` и проверяет sha256.
6. `update verify` проверяет staged artifact и identity из package manifest внутри zip.
7. `update apply --confirm` создаёт backup, применяет поддержанное локальное обновление и обновляет installed subjects.
8. `update rollback` восстанавливает backup.

Автоматического apply нет. Tool policy `custom_command_requires_confirmation` блокируется по умолчанию; ProcessForge не исполняет произвольные remote postinstall scripts.
