# ProcessForge 1.3.0-alpha5

This alpha fixes Core identity reporting across CLI, Runtime, monitor, MCP and
Host. A shared CoreProperties object reads the owning distribution's metadata;
adapters no longer report a duplicated release constant from the CLI facade.

The process keeps an immutable loaded identity. A separate live observation
reports the metadata currently installed on disk. Updating files therefore does
not make an existing process claim that it has loaded the new release. Reload
or reconnect long-running applications after an update to load the new Core.
Missing or inconsistent metadata produces an explicit unknown result.

Release, Runtime component, protocol, spec and schema versions remain separate.
Published CLI/MCP parameters and response fields are preserved. The Core owner
supports constructor injection and library/file-only use without launching a
transport or loading the CLI facade.

Runtime/Host state schema2 adds portable `core_identity`; MCP action discovery
provenance contract2 reports loaded and installed builds and names reconnect
when they differ. Runtime doctor now diagnoses a changed build even when its
release label is unchanged. Older state without build evidence remains unknown.
MCP initialize, protocol and tool input schemas retain their existing contracts.

This release includes the earlier alpha changes, including explicit shared
search-index maintenance and verified SQLite maintenance/recovery. It remains
an opt-in prerelease; stable 1.2.0 remains the stable release. Installation uses
the existing explicit update confirmation and preservation process.

See [Core properties](../../docs/concepts/core-properties.md) for the identity
contract, provenance limits and loaded-versus-installed behavior. Source,
archive, installed and connected-host qualification are distinct evidence.
