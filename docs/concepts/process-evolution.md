# Process Evolution

Process versions are immutable. A running or completed process cannot be silently moved to a new version when that change could break achieved results.

## Policy Location

Upgrade policy belongs in each process definition because each process has different protected artifacts and compatibility rules.

## Compatibility Questions

- Which artifact definitions changed?
- Which artifact instances already exist?
- Which artifacts are approved?
- Which artifacts are protected?
- Which artifacts can migrate?
- Which artifacts require revalidation?
- Which gates must rerun?
- Which results would be invalidated?

If the new process version cannot explain what happens to existing approved or protected artifacts, the upgrade is blocked.
