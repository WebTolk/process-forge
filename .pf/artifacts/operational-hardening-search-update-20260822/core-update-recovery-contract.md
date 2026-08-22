# Core Update Recovery Contract

Run: `operational-hardening-search-update-20260822`

## Incomplete State Classes

- `nothing_to_repair`: no incomplete update exists.
- `safe_to_rollback`: update failed before manifest write, old manifest backup exists, and the operation journal is readable.
- `manual_repair_required`: manifest was written, journal is incomplete/unreadable, or safety cannot be proven.

## Journal Fields

- `installed_version`
- `target_version`
- `archive`
- `backup_dir`
- `counts`
- `completed_operations`
- `pending_operations`
- `backed_up`
- `error`

## Rule

Automated recovery may only be added for states that the journal proves safe. Unknown state must remain manual.
