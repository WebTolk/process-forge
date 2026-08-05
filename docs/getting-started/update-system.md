# Update System

Use the unified updater from a workplace root. It discovers update servers,
finds candidates, stages an artifact, verifies it, and applies supported
file-based updates only after explicit operator confirmation:

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

For deterministic local testing, use `file:///` manifest and artifact URLs.
For real remote update servers, use HTTPS URLs, sha256 hashes, and operator
review before staging or applying.

## Updating The Installed ProcessForge Core

Do not unpack a ProcessForge release into a project `.pf` directory. Update the
installed ProcessForge distribution; workplaces and projects stay separate.

Recommended manual flow:

1. Extract `processforge.zip` to a new versioned directory outside the project,
   for example `<processforge-root-1.0.1>`.
2. Verify the new distribution:

   ```powershell
   python <processforge-root-1.0.1>/bin/pf.py version
   python <processforge-root-1.0.1>/bin/pf.py release-test --root <processforge-root-1.0.1> --public
   ```

3. Update `<workplace>/registries/distributions.yaml` so the `processforge`
   entry points to the new directory and version.
4. Validate the workplace:

   ```powershell
   python <processforge-root-1.0.1>/bin/pf.py doctor-workplace --workplace <workplace>
   ```

5. For each linked project, assess and refresh the project context:

   ```powershell
   python <processforge-root-1.0.1>/bin/pf.py project-upgrade-check --project-root <project>
   python <processforge-root-1.0.1>/bin/pf.py project-context-refresh --project-root <project>
   python <processforge-root-1.0.1>/bin/pf.py project-context-check --project-root <project>
   python <processforge-root-1.0.1>/bin/pf.py doctor-project --project-root <project>
   ```

Keep the previous distribution directory until validation passes. To roll back,
repoint `registries/distributions.yaml` to the previous version and rerun the
workplace and project doctors.

Overlaying the new archive on top of the old directory is only a manual
recovery option after a backup. It can leave files that were removed from the
new release.

## Updating Project `.pf`

Project `.pf` is not updated through package overlay. Use:

```bash
python bin/pf.py project-upgrade-check --project-root <project>
```

The command writes an assessment/migration report under the project
`.pf/artifacts/` directory and does not modify project files automatically.

After the assessment:

1. Read the report and the migration guide for the target ProcessForge version.
2. If no migration is required, refresh and validate the context snapshot:

   ```bash
   python bin/pf.py project-context-refresh --project-root <project>
   python bin/pf.py project-context-check --project-root <project>
   python bin/pf.py doctor-project --project-root <project>
   ```

3. If the report requires project `.pf` changes, apply them explicitly through
   the relevant ProcessForge process or CLI command, then rerun the context and
   project doctors.

For ProcessForge `1.0.1`, no project `.pf` migration is required. Existing
assignments and capsules remain valid; new shell-agent flows may use
`workspace_access` to grant workplace knowledge, templates, tools, and MCP
through a private runtime access file.
