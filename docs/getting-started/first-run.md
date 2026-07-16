# First Run

First run has two separate processes:

- `workplace-initialization`: prepares the local workplace, registries, packages, tools, and knowledge roots.
- `project-onboarding`: creates a project-local `.pf/` and links that project to the existing workplace.

The convenience `first-run` command only runs those two processes in order. It is not a third process.

Python CLI is the canonical runtime. The root `pf` wrappers are thin convenience launchers over `bin/pf.py`.

```bash
python tools/processforge.py first-run --workplace ./pf-workplace --project-root ./my-project --type generic-software-project --apply
```

For explicit control, run the two commands separately:

```bash
python tools/processforge.py workplace-init --workplace ./pf-workplace --apply
python tools/processforge.py project-onboard --project-root ./my-project --workplace ./pf-workplace --type generic-software-project --apply
python tools/processforge.py agent-start-prompt --project-root ./my-project
```

Inside `./my-project`, run ProcessForge through `pf` or the project-local runtime launcher:

```bash
pf doctor-project --project-root .
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Do not call `python tools/processforge.py` from a normal linked project root.
