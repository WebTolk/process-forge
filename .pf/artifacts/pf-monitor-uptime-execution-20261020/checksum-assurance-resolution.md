# Checksum gate resolution

The first complete public source test attempt stopped at the checksum gate.
Native validation reported exactly two inventory-only rows for alpha publication
metadata, outside the validator's actual public file set:

```text
2cd4e3377902caf470c560d7adf06fd5a54bcebf68a4a1edddd89995656a1843  release/updates/processforge-alpha.json
f6bf94bec5fe6ba6bd52979162901fae3bc6457a0a974673e3d07acdf4fe0f7f  release/1.3.0-alpha1/processforge-1.3.0-alpha1.manifest.json
```

The diagnostic label `expected only` denotes existing inventory entries absent
from the actual computed set; it does not denote missing inventory rows. The
validator's `PUBLIC_DIRS` excludes `release/`. The initial interpretation was
corrected before any inventory mutation.

Assurance removes only these two native-reported rows from the authorized
inventory. The existing release files and all product source bytes are unchanged.
This restores the inventory prerequisite for the requested complete test gate;
it is not another backlog implementation or a new alpha publication. The failed
attempt and original sealed manifest are retained under the task-private
`attempt-1` directory. A new sealed manifest records this inventory-only repair.
The complete canonical suite must be rerun after native checksum validation.
