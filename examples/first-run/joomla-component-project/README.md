# Joomla Component Project Onboarding Example

Onboard a Joomla component project after the workplace exists:

```bash
python tools/processforge.py project-onboard --project-root ./com_example --workplace ./pf-workplace --type joomla-component --apply
python tools/processforge.py doctor-project --project-root ./com_example
```

For a strict Joomla workflow, install or register the Joomla platform contract in the workplace before onboarding:

```bash
python tools/processforge.py platform-contract-install --workplace ./pf-workplace --id joomla --required-capabilities repository.read --apply
```

The project onboarding process must report missing required platform contracts instead of silently guessing.
