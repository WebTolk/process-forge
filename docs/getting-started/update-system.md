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

### First managed update from 1.0.2 to 1.1.0

The public 1.0.2 distribution does not contain the manifest-based core updater.
For this one transition, extract the 1.1.0 archive to a temporary staging
directory and run the new updater from that directory against the stable
installed Core path.

1. Back up the installed Core and stop its optional long-lived PF Runtime.
2. Extract `processforge-1.1.0.zip` to `<staged-processforge-1.1.0>`.
3. Verify the staged distribution:

   ```powershell
   python <staged-processforge-1.1.0>/bin/pf.py version
   python <staged-processforge-1.1.0>/bin/pf.py release-test --root <staged-processforge-1.1.0> --public
   ```

4. Plan and explicitly apply the update to the stable installed directory:

   ```powershell
   python <staged-processforge-1.1.0>/bin/pf.py core-update plan --core-root <installed-processforge> --archive <processforge-1.1.0.zip>
   python <staged-processforge-1.1.0>/bin/pf.py core-update apply --core-root <installed-processforge> --archive <processforge-1.1.0.zip> --confirm
   ```

5. Validate the installed Core and workplace, then restart PF Runtime when it is
   configured:

   ```powershell
   python <installed-processforge>/bin/pf.py version
   python <installed-processforge>/bin/pf.py core-update status --core-root <installed-processforge>
   python <installed-processforge>/bin/pf.py doctor-workplace --root <workplace>
   ```

6. For each linked project, run `project-upgrade-check`, refresh the context,
   and run `doctor-project` with the installed 1.1.0 CLI.

The updater writes backups and an operation journal before replacing managed
files. Use `core-update status` and `core-update repair` if an interrupted update
is reported. Future releases can use the updater already installed by 1.1.0.

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

For ProcessForge `1.1.0`, no mandatory project `.pf` migration is required.
Existing assignments and capsules remain valid. Refresh project context and
search indexes so Garage, MCP, and Runtime use current resource snapshots.
