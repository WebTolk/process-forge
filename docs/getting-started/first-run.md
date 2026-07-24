# First Run

First run has two separate processes:

- `workplace-initialization`: prepares the local workplace, registries, packages, tools, and knowledge roots.
- `guided-workplace-setup`: optionally guides the operator through answers, proposal, review, apply report, agent snippet, and next steps.
- `project-onboarding`: creates a project-local `.pf/` and links that project to the existing workplace.

The convenience `first-run` command only runs those two processes in order. It is not a third process.

Python CLI is the canonical runtime. The root `pf` wrappers are thin convenience launchers over `bin/pf.py`.

```bash
python bin/pf.py first-run --workplace ./pf-workplace --project-root ./my-project --type generic-software-project --apply
```

For explicit control, run the two commands separately:

```bash
python bin/pf.py workplace-init --workplace ./pf-workplace --apply
python bin/pf.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python bin/pf.py agent-start-prompt --project-root ./my-project
```

Inside `./my-project`, run ProcessForge through `pf` or the project-local runtime launcher:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Do not call `python bin/pf.py` from a normal linked project root.

For a full setup, follow [Initialization order](initialization-order.md): install and verify ProcessForge, initialize workplace, configure roots including `knowledge_roots.local-docs`, register tools and MCP servers, create or import knowledge packages and templates, then create platform contracts and onboard projects.

For a chat-led first machine setup, use [Guided workplace setup](guided-workplace-setup.md).

Do not start with a platform contract if its required packages, templates, or tools do not exist yet. Create or register dependencies first.
