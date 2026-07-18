# Tools

ProcessForge tools are local validators for file-only mode.

## Commands

```bash
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
python bin/pf.py workplace-init --workplace <workplace-root> --dry-run
python bin/pf.py workplace-init --workplace <workplace-root> --apply
python bin/pf.py doctor-workplace --root <workplace-root>
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --dry-run
python bin/pf.py project-onboard --project-root <project-root> --workplace <workplace-root> --type generic-software-project --apply
python bin/pf.py doctor-project --project-root <project-root>
python bin/pf.py session-start --mode resume --project-root <project-root>
python bin/pf.py context-resolve --project-root <project-root>
python bin/pf.py context-compile --project-root <project-root> --assignment <assignment-path> --capsule
python bin/pf.py doctor-context --project-root <project-root>
```

The tools use only the Python standard library.
