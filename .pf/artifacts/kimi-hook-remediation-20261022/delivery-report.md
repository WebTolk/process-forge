# Source delivery

2026-10-22. Qualified source commit c38b4b09710cf88a336bcf78e86b04c5e78c70dc was pushed and read back from both origin/dev and gitverse/dev. GitVerse used the existing token-backed askpass helper with credential-manager bypass; token values were not emitted. Earlier review/restoration commits are included in this history.

All seven historical capsule preimages are restored and included, with live/pinned bytes unchanged. The separate restoration commit fbde6710df9ff2eaf5eea3a408695b4d33a21367 restores the other 70 pre-existing blobs. Qualified fixes/tests and safe reports are committed; unrelated dirty work is excluded.

Source readiness: PASS on the bounded Kimi scope, including 85 tests, 13 subtests, Ruff lint/format, mypy and provider admission. This source slice neither installs Core nor claims real Kimi acceptance. The user's subsequent dev release/device installation request has a separate valid Work: garage-kimi-dev-device-20261022-complete-the-user-s-explicitly-authorize, assignment kimi-dev-device-20261022-complete-the-user-s-explicitly-authorized-local. Its native operator grants own archive/install/Runtime qualification.

Handoff: use this exact committed source for the clean dev candidate. Preserve source versus installed versus running-host evidence; the real Kimi model rerun remains with the user. No public stable publication is required by this source slice.
