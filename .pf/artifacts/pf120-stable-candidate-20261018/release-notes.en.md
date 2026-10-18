# ProcessForge 1.2.0

An intermediate checkpoint in the continuing Core refactoring, with cumulative reliability, storage and performance changes. Existing CLI/MCP and governed Work boundaries remain in force; the complete OOP migration continues separately.

- Project event and native hook journals use separate local SQLite databases with transactional admissions and indexed replay. Existing history needs an explicit, controlled cutover; Core installation does not import or delete legacy journals.
- Safe YAML parsing reuses unchanged content in bounded process-local memory. Work/context reads share compact metadata while retaining live authorization, pinning and full selected-Work validation.
- Runtime operational health follows scheduler execution while worker failures and collection recovery remain visible as task outcomes. Partial metrics keep their coverage issues and unknown values.
- Automatic Garage hooks are opt-in. Forge remains governed; admitted native lifecycle hooks manage session registration and checkout.
- Publication cleans only its own failed staging file and preserves the destination/error. Supervisor history and stable collect refusal avoid automatic repetition without bypassing explicit recovery checks.
- Project entry uses root AGENTS.md and current PF context; existing START files and historical process/capsule versions remain preserved.

Review [migration guidance](https://github.com/WebTolk/process-forge/blob/v1.2.0/docs/releases/1.2.0-migration.md) and [qualification limits](https://github.com/WebTolk/process-forge/blob/v1.2.0/docs/releases/1.2.0.md). In particular, preserve journal backups, local storage and explicit operator lifecycle control; restarting Runtime does not prove that a connected MCP host loaded new code.

Windows qualification does not establish Linux/macOS or every Python-version combination. Large histories can still affect scheduler/admission cost. Device timings describe the measured workload, not a universal performance guarantee.

A guarded shutdown can refuse when its bounded observer cannot establish complete idle state on retained worker history. Preserve that refusal and inspect complete native state through the operator lifecycle procedure; partial metrics are not zero.

The ZIP and separate manifest will identify the exact tagged source commit and final SHA256. The stable update channel is promoted only after immutable release assets are verified. Discovery does not authorize installation; application still requires explicit confirmation.
