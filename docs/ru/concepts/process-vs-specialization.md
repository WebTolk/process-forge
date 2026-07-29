# Process vs Specialization

ProcessForge разделяет workflow процесса и resource profile специалиста.

Process владеет execution route: stages, gates, acceptance criteria, required
artifacts, required evidence и abstract capability requirements. Process может
сказать, что stage требует capability, но не должен привязывать корректность
workflow к конкретной specialization, tool или platform-specific package.

Specialization владеет active resource profile: knowledge packages, templates,
tools, MCP providers и capabilities, доступными специалисту для выбранного
platform stack и проекта. Это не mini-process, не platform subtype и не agent
identity.

Resolution соединяет две модели:

```text
specialist / specialization + project + platform stack + project overrides
= active resource profile

task + process
= execution route

active resource profile + execution route + task scope
= resolved context snapshot / capsule
```

Если process требует capability, которую selected specialization/platform
binding не предоставляет, resolver записывает unsatisfied capability. Он не
переключает specialization автоматически; для этого нужно явное решение
оператора или Director routing.

PF core не интерпретирует capability IDs. Он не знает, относится ли capability к
software, web, music, video, legal, research или любому другому домену. Active
resource profile должен предоставить opaque ID через данные, иначе requirement
остается `unsatisfied`.

Примеры в документации и smoke tests используют только `fixture.*` или
`example.*` IDs.
