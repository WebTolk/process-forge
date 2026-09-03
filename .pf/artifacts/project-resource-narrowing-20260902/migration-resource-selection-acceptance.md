# Migration Resource Selection Acceptance

Status: pass

The legacy migration fixture selected `5.4.5` when the generic target was
`5.4`, then selected `6.1.2` when the target was `6.1`. The target is data in
the context requirements and is not coupled to a Joomla branch in core code.

The same smoke verifies that selection provenance records the fallback reason
and that legacy documentation receives the bounded full-text migration policy.
