# T08 archive validation

2026-09-25. Clean candidate a180ad624442d4fbe8ac1710073ef7d4c44babc4.

`release-pack --root . --output <t08-package>/processforge-1.1.0-a180ad6.zip`: exit 0,
955 entries, public cleanliness and checksum inventory preflights passed.

`release-archive-test --root <clean-candidate> --archive <t08-package>/processforge-1.1.0-a180ad6.zip --extracted-test quick`: exit 0, RESULT: PASS.
Archive/sidecar schema, source provenance dirty=false, safe entries, ownership and file hash
parity with clean source all PASS. No forbidden entries.
Extracted bin/pf.py --help PASS (6.27s), tools/processforge.py --help PASS (1.32s).
Extracted release-test quick PASS, 162.90s, finished 2026-09-25T14:30:10Z.
Quick covers py_compile, schema validation, public cleanliness, checksum,
smoke_processforge_core_package_bootstrap, smoke_central_event_ingress,
smoke_conversation_completeness, smoke_central_event_replay.

Archive SHA256: 324932d147aecb1ad7d1511735a7d69d4391c6220eb3dbc5e18e2d7ecbce6008.
Sidecar SHA256: 8bf1220eaa1351fdb00307f1a3d5318e0e25583c6b8d77c0ab127e9975de60d7.
This is a bounded teststand delivery, not a full public-release qualification.
