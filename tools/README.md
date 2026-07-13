# Tools

ProcessForge tools are local validators for file-only mode.

## Commands

```bash
python tools/validate-process-forge-schemas.py
python tools/validate-process-forge-checksums.py
python tools/validate-public-cleanliness.py
python tools/processforge.py init-workplace --root <workplace-root> --dry-run
python tools/processforge.py init-workplace --root <workplace-root> --apply
python tools/processforge.py doctor-workplace --root <workplace-root>
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --dry-run
python tools/processforge.py init-project --project-root <project-root> --workplace <workplace.yaml> --apply
python tools/processforge.py doctor-project --project-root <project-root>
python tools/processforge.py session-start --mode resume --project-root <project-root>
python tools/processforge.py context-resolve --project-root <project-root>
python tools/processforge.py context-compile --project-root <project-root> --assignment <assignment-path> --capsule
python tools/processforge.py doctor-context --project-root <project-root>
```

The tools use only the Python standard library.
