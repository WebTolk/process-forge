# Installation

ProcessForge is installed as a file-first Python tool. Clone or unpack the
distribution once, then use it to initialize a workplace and onboard projects.

```bash
git clone <processforge-repo> process-forge
cd process-forge

python bin/pf.py version
python bin/pf.py release-test --root .
```

Use `python bin/pf.py` from the ProcessForge distribution root.

After a project is onboarded, use the project runtime launcher inside that
project:

```bash
python .pf/runtime/bin/pf.py doctor-project --project-root .
```

Do not copy the full ProcessForge repository into `.codex`, `.claude`,
`.agents`, or similar agent configuration folders. The agent configuration only
needs a short instruction that points to the tool installation and tells the
agent to read `.pf/START_AGENT_HERE.md` inside the project.

## Verify The Installation

```bash
python tools/validate-public-cleanliness.py --root .
python tools/validate-process-forge-checksums.py --root . --check
python bin/pf.py release-test --root .
```
