# Real Joomla Resource Narrowing Acceptance

Status: pass

The real Joomla context shape was built without persisting changes to the
external project. The resolver retained direct resources and exactly one
current compatible core source instance, `6.1.2`. It did not retain v1-v5 or
the older 6.1 patch instances.

Acceptance command: `python tools/smoke_project_resource_narrowing_search.py`.
