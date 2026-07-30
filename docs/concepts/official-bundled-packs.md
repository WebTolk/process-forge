# Official Bundled Process Packs

ProcessForge separates four layers:

1. the domain-neutral kernel and system processes;
2. official bundled process packs;
3. examples and fixtures;
4. workplace, project, and custom resources.

An official bundled pack is production-grade versioned data shipped in
`packs/official/`. Its manifest declares that it is official, bundled, available
from the distribution, inactive by default, and not a runtime dependency.
Processes, prompts, documentation, templates, classifiers, and knowledge
packages are resolved from the pack data rather than from domain-specific
branches in `tools/processforge.py`.

Official packs are both immediately usable workflows and architecture
references for custom packs. They play a role similar to bundled Joomla
extensions: useful out of the box, but separate from the kernel that loads
them.

Availability and activation are distinct:

- available means the distribution can discover the pack;
- registered means a workplace records it;
- active means its resources participate in resolution;
- selected means a project or session chose it for the current work.

The `generic` profile activates no domain pack. A named profile or
`pack-activate` may activate one explicitly. Merely finding a marker such as
`composer.json` never activates a pack or classifier.

Examples may demonstrate an official process, but the canonical process
definition and its stable id belong to the official pack.
