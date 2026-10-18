# Development checkpoint: OOP project metadata

Development version: 1.1.0. Executable source commit: `352592173c44d35a2488a837e2e4d6ca1c434bf2`.
Clean source tree: `18b4d0f583df67afefae87de035dccbf634638cc`. Archive SHA-256: `0158218618c5b24cc6b505e1a2fab2876a3f9efd86566ae0d567b8583b8b9147`.

The accepted project-context metadata migration uses the existing concrete `ProjectMetadataReader` for project identity and manifest operations. Two metadata callback fields and their legacy bindings were removed; affected production composition and test consumers were migrated. Other context callbacks remain unported, and all five OOP epics remain open.

The cumulative archive also includes the reviewed MCP UTF-8 stdio companion fix and a byte-preserving metadata test fixture spelling fix. The latter retains all seven test methods, four generated YAML payloads and the existing public-cleanliness guard. No new Core feature, storage format, DI framework or permission mechanism was introduced.

Qualification:

- Clean committed source, release and Core manifests agree. All 1227 owned payloads and 1,228 release members were checked by size and SHA-256; eight selected committed metadata/Unicode payloads match exactly.
- Native extracted quick coverage passed eight selected checks. Focused metadata, mode, snapshot and Unicode checks passed; the full public suite was not repeated.
- A native artifact executor and an independent reviewer reproduced owned-byte, default metadata, copied-Core and controlled Unicode checks. Worker `TemporaryDirectory` failures were preserved; private inherited scratch allocation retained the original tests and assertions. Source, archive and runtime evidence remain separate.
- The manifest update was applied once. The ownership delta was five additions, ten changes and no removals. The existing unchanged local manifest was preserved; no updater force was used. Installed owned bytes, native backup preimages, project/workplace configuration and protected history were verified.
- Focused installed metadata, Unicode, JSON-RPC, project-context and project-doctor checks passed. A fresh independent stdio process, using the normal installed bootstrap without fixture or module patching, successfully initialized and read the actual fresh project context. The owned Runtime started from the verified installation with a new process identity and reached ready state. Existing scheduler/metrics diagnostic limits were retained as a separate baseline.

The connected MCP host predates this update and remains unqualified for the newly installed modules until an actual fresh host process and requests are verified. A new Runtime process or fresh independent stdio process does not establish connected-host qualification. Installed CLI operations use this verified executable source.

This note and its checksum are published after installation as a separate documentation commit. They are not part of the executable archive identified above. Source and both remote publication receipts, independent review, archive, installation, backup, history and Runtime evidence are retained in private governed records; credentials and device-specific paths are excluded from this note.
