# Система обновлений

Минимальный локальный сценарий:

```bash
python bin/pf.py update entity-sources rebuild --workplace <workplace>
python bin/pf.py update candidates refresh --workplace <workplace>
python bin/pf.py update candidates list --workplace <workplace>
python bin/pf.py update notifications list --workplace <workplace>
python bin/pf.py update changelog show --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update stage --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update verify --workplace <workplace> --candidate <candidate-id>
python bin/pf.py update apply --workplace <workplace> --candidate <candidate-id> --confirm
python bin/pf.py update rollback --workplace <workplace> --candidate <candidate-id>
```

Для публичных deterministic tests используйте `provider: processforge_json_file` и `file:///` URLs. Для remote update site используйте `processforge_json`, HTTPS, sha256 и ручное подтверждение оператора.

Project `.pf` обновляется отдельно:

```bash
python bin/pf.py project-upgrade-check --project-root <project>
```
