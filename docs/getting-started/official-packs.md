# Official Packs

List production packs bundled with ProcessForge:

```bash
python bin/pf.py pack-list --origin official --available
python bin/pf.py process-list --origin official --available
```

A generic workplace keeps them available but inactive:

```bash
python bin/pf.py workplace-init --profile generic --workplace ./pf-workplace --apply
```

Activate the software workflow either through initialization or explicitly:

```bash
python bin/pf.py workplace-init --profile software-development --workplace ./pf-workplace --apply
python bin/pf.py pack-activate --id processforge.official.software-development --workplace ./pf-workplace --apply
```

Inspect the resulting catalog:

```bash
python bin/pf.py process-list --active --project-root ./my-project --workplace ./pf-workplace
python bin/pf.py process-show software-feature-development --project-root ./my-project --workplace ./pf-workplace
```

The process is used directly from the distribution. Do not copy its definition
from `examples/`. If an available process is not active, ProcessForge reports
the owning pack and the activation command.

Official packs are normal data packs. Use the process and package authoring
tools to build custom workflows with the same separation from the kernel.
