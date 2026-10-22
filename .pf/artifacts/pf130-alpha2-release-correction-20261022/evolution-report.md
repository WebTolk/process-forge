# Version correction lesson

The primary incorrectly reused an already-released alpha1 identity for a new dev
delivery. An archive hash/source SHA distinguishes bytes but does not replace the
operator's release-version decision. This cycle corrects the actual source values,
package metadata and installed device version to alpha2, preserving prior receipts.

Before packaging, explicitly reconcile VERSION, archive identity, intended target
and release history. Before apply, assert that the updater plan selects the exact
target version. Verify installed CLI and manifest afterward; preserve the separate
Runtime/protocol/spec identities and existing-host lifetime distinction.

PF-selected Python/prerelease guidance and Core/OOP boundaries were read. The
correction reused the existing identity owner; it did not turn the separate
Core-properties planning task into an implementation or change domain behavior.
Existing tests plus archive comparison provided bounded meaningful assurance.
Stop after this corrected dev delivery and native lifecycle closure.
