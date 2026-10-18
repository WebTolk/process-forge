# Implementation

Local index now defaults current/latest1.2.0, points changelog to v1.2.0 and adds one1.2.0 catalog record with existing migration guide and checkpoint date matching CHANGELOG. Historical version entries and official manifest URL retained. No Python, parser, runtime, process/capsule or online stable feed changes.

Inventory generated with native --write in clean LF c4d6649 worktree overlaid with the sole YAML change, then copied back; expected delta exactly one public entry. Product scope exactly YAML+inventory; unrelated workspace/index preserved. Handoff: targeted checks and native schema/cleanliness/checksum/release gates, primary review, parent requalification on exact final commit.
