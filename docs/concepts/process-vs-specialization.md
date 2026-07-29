# Process vs Specialization

ProcessForge keeps process workflow and specialist resource profiles separate.

Process owns the execution route: stages, gates, acceptance criteria, required
artifacts, required evidence, and abstract capability requirements. A process
can say that an acceptance stage requires a verification capability, but it must
not name a concrete specialization, tool, or platform-specific package as the
source of workflow correctness.

Specialization owns the active resource profile: knowledge packages, templates,
tools, MCP providers, and capabilities available to a specialist for a selected
platform stack and project. It is not a mini-process, not a platform subtype,
and not an agent identity.

Resolution joins the two models:

```text
specialist / specialization + project + platform stack + project overrides
= active resource profile

task + process
= execution route

active resource profile + execution route + task scope
= resolved context snapshot / capsule
```

If a process requires a capability that the selected specialization/platform
binding does not provide, the resolver reports an unsatisfied capability. It
does not silently switch specialization; that requires an explicit operator or
Director routing decision.

ProcessForge core does not interpret capability ids. It does not know whether a
capability belongs to software, web, music, video, legal, research, or any other
domain. The active resource profile must provide the opaque id through data, or
the requirement remains unsatisfied.

Examples in documentation and smoke tests use `fixture.*` or `example.*` ids
only.
