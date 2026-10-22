# Existing migration smoke adaptation

Primary changed only `tools/smoke_hook_sqlite_migration.py` in this bounded Work.
The old smoke injected failures into the formerly monolithic migration script.
The script now delegates to Core, so injection targets the actual scanner and
raw-journal owners. Existing successful migration, failure and barrier checks
remain; `MaintenanceError` participates in the expected refusal assertions.

The adapted smoke passed after implementation and the Windows scanner correction.
Final source bytes are pinned by
[candidate r3](../primary/source-candidate-r3.json) and committed as
`0bcf2a274a2097cf2ec84aa3a084644039390406`. Both dev remotes match that commit.
The complete public delivery suite will execute the smoke again.

The integrated [test report](../primary/test-report-r2.md),
[quality report](../primary/code-quality-report-r2.md) and independent
[CODE GO](../review/r2/report.md) cover this final version. No product or fixture
behavior was weakened to make checks pass. Scope contains no release publication;
the parent owns native source/archive qualification and alpha3 publication.

Handoff: keep failure injection attached to the layer owning the operation after
an extraction. No separate improvement or implementation task remains here.
