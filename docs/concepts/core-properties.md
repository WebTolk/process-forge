# Core Properties

`processforge_core.common.properties` owns the metadata identity of the selected
Core distribution. CLI, Runtime, monitor, MCP and Host consume that owner through
their existing version fields. The internal object contract is part of the
incremental [Python Core structure](python-core-structure.md); it does not complete
the wider OOP migration or add a stable public transport API.

## Ownership and composition

The cohesive module contains four related types:

| Type | Responsibility |
| --- | --- |
| `CoreIdentity` | Frozen value containing the strings `version`, `build_id`, `source_commit`, `source_kind`, `status` and `reason`. |
| `CoreIdentityReadPort` | Narrow structural dependency: `read() -> CoreIdentity`. |
| `DistributionMetadataReader(distribution_root)` | Bounded metadata reads from one explicitly selected distribution. |
| `CoreProperties(reader)` | Capture one loaded value and expose separate live disk observations. |

Normal application composition uses one shared factory:

```python
from processforge_core.composition import build_core_properties

properties = build_core_properties()
loaded = properties.loaded
installed_now = properties.installed()
```

The factory creates one properties object on its first call, under a lock, using
the root derived from its own Core module in the distribution's `src/` layout.
The CLI facade calls it at boot; `RuntimeBootstrap.properties` returns the same
object. This application lifetime retains an immutable identity and a reader
bound to that distribution, without current project, Work, grants or request
documents. No DI container or service locator is needed for this responsibility.

Library callers and fixtures can inject a reader without loading CLI or Host:

```python
from processforge_core.common.properties import (
    CoreProperties,
    DistributionMetadataReader,
)

# selected_root is the explicitly supplied distribution root.
properties = CoreProperties(DistributionMetadataReader(selected_root))
```

`CoreProperties.from_distribution(selected_root)` composes the same concrete
reader. These constructors and types grant no filesystem or Work permissions.
Reading properties does not start Runtime/MCP, refresh context, query the network
or scan Git status/history.

## Loaded identity and installed observation

`loaded` is captured once when the service is constructed. Disk updates do not
replace that frozen value. Each `installed()` call rereads metadata at the same
bound root. A newly constructed service can capture the updated metadata; calling
`build_core_properties()` again in the existing process returns its original
object.

The current working directory and neighbouring installations do not select the
default distribution. Moving the whole distribution before a new process starts
lets the factory use its relocated module root. An existing reader retains its
resolved original root; it does not follow a directory move or discover another
installation. These semantics do not prove a real restart, reconnect or update.

## Metadata provenance and limits

`VERSION` owns the release label, including prerelease/build suffixes. The reader
accepts bounded UTF-8 metadata: up to 1 KiB for `VERSION` and 8 MiB for
`processforge-core.manifest.json`. A present manifest must pass the existing
native file-map validation and agree with `VERSION`; malformed metadata does not
fall back to a release literal or a Git ref.

| Metadata source | Identity |
| --- | --- |
| Usable Core manifest | `source_kind="manifest"`; `build_id="manifest:sha256:<digest>"` hashes the exact manifest bytes; `source_commit` comes from a valid hexadecimal `source.commit`. |
| No manifest, readable Git HEAD/ref | `source_kind="source_checkout"`; `source_commit` is the observed ref and `build_id="git:<commit>"`. |
| Valid VERSION without a usable build/revision | The version remains known; unavailable identity fields are `unknown` and status is `partial`. |

Git observation is bounded and read-only, supporting detached HEAD, worktree
pointers and packed refs. It does not verify commit object existence, provenance
authenticity or an unmodified working tree. Manifest hashing identifies metadata
bytes, including serialization and timestamp changes. Equal release labels can
therefore have different build IDs. Neither a manifest digest nor a Git ref
verifies payload file contents; archive/update hash qualification remains a
separate check under the [Core update manifest](core-update-manifest.md) contract.
`source_kind` describes the observed metadata source, not an accepted archive or
installation.

`status="ready"` means the reader obtained the metadata fields, with an empty
reason. `partial` retains known fields and explains unavailable provenance.
`unknown` accompanies unusable required metadata rather than a guessed version:

| Condition | Bounded reason |
| --- | --- |
| Missing or invalid VERSION | `version_missing` or `version_invalid` |
| Invalid manifest or release-label disagreement | `manifest_invalid` or `version_manifest_mismatch` |
| Metadata exceeds a read limit or cannot be read | `metadata_too_large` or `metadata_unreadable` |
| VERSION/manifest changes during the verification reread | `metadata_changed` |
| Manifest lacks a usable source revision | `source_revision_unavailable` (`partial`) |
| No manifest and no usable Git revision | `build_metadata_unavailable` (`partial`) |

The value includes neither private roots nor exception text. Reasons are
available through the object contract; existing transport schemas gain no keys.

## Independent versions and adapters

| Existing surface | Meaning |
| --- | --- |
| CLI `version` release line | `loaded.version`; the three-line output retains separate Spec and Schema bundle lines. |
| Runtime/Host `processforge_core_version` | The loaded Core release of the reporting process. |
| Runtime `installed_pf.version` | A live disk observation from the calling process's bound distribution. |
| Monitor `cli_version` | Loaded Core of the CLI running the monitor. |
| MCP `serverInfo.version` and action discovery version | Loaded Core of the serving MCP process. |
| `spec_version` and `schema_bundle_version` | Existing specification/schema bundle versions, both `1.0`. |
| Runtime `instance_version` / component version | Independent Runtime component version, currently `1.0.0-poc`. |
| Runtime and MCP protocol versions | Their separate compatibility contracts (`pf-runtime-poc-1` and `2024-11-05`). |

The current Runtime doctor compares its recorded Core version with the current
installed version. This version comparison cannot detect a changed build with an
unchanged label; the object-level build IDs remain separate from existing payloads.

Source/import checks, a package-shaped relocation fixture, a clean committed
release archive, a device installation and a real connected host are separate
evidence boundaries. Fixture metadata observations do not qualify archive
integrity, device preservation or restart/reconnect behavior. See the
[Runtime model](runtime-model.md) and [release checklist](../release-checklist.md)
for their existing operational contracts.
