# ProcessForge 1.2.1 Candidate Hardening

- Result: PASS for candidate and extracted archive qualification
- Candidate source: isolated local clone of `D:\Dev\process-forge`
- Candidate commit: `7c5883b5d03d649931f2e40c660f4817e79efd64`
- Version: `1.2.1`
- Archive: `C:\Users\musst\AppData\Local\Temp\pf-machine-acceptance-20260829-release\processforge-1.2.1.zip`
- Archive size: 1,313,274 bytes
- Archive files: 891
- SHA-256: `fc79ce7f1fb21ac1fa80acf21e2dc673847510b86aa719d1fda09a965384a767`

## Confirmed Remediations

- Inherited host environment values are no longer persisted in worker `command.json`; inheritance is materialized only for process launch.
- Public release smokes no longer contain machine-local paths or domain-specific fixture identifiers.
- Search maintenance, Garage search, and `pf.session_context` now resolve authorized resources through one Garage runtime-snapshot resolver.

## Verification

- Public cleanliness: PASS
- Checksum inventory: PASS
- Release check: PASS
- Focused post-fix release suite: PASS, 172.27 seconds
- ZIP manifest/provenance/hash/file parity: PASS
- Full public release suite from extracted ZIP: PASS, 1080.98 seconds

The candidate is local and unpublished. No source commit, tag, or remote branch was created outside the isolated clone.
