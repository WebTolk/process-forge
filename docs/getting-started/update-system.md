# Update System

Use the unified updater from a workplace root:

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

For deterministic local testing, use `provider: processforge_json_file` and `file:///` manifest/artifact URLs. For real remote update sites, use `provider: processforge_json`, HTTPS URLs, sha256 hashes, and operator review before staging or applying.

Project `.pf` is not updated through package overlay. Use:

```bash
python bin/pf.py project-upgrade-check --project-root <project>
```

The command writes an assessment/migration report under the project `.pf/artifacts/` directory.
