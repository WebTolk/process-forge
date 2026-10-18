"""Execute the published compatibility example only in an isolated PF fixture."""
from pathlib import Path
import re
import shlex
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import smoke_process_run_task_batch as fixture
import processforge as core

text = (ROOT / "docs/getting-started/task-batch-workflow.md").read_text(encoding="utf-8")
commands = [shlex.split(line)[2:] for block in re.findall(r"```bash\n(.*?)```", text, re.S)
            for line in block.splitlines() if line.startswith("python ")]
allowed = {"run-create", "task-create", "iteration-add", "task-complete", "run-summary", "run-doctor", "run-complete", "run-status"}
assert commands and all(args[0] in allowed for args in commands)
parent = ROOT / ".pf/tmp"
parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="docs-example-", dir=parent) as tmp:
    project = fixture.make_project(Path(tmp), "documented-batch")
    # Satisfy the documented operator-owned precondition in this fixture only.
    fixture.pf("pack-activate", "--id", "processforge.official.software-development",
               "--workplace", str(Path(tmp) / "documented-batch-workplace"), "--apply")
    fixture.pf("pack-activate", "--id", "processforge.official.verification",
               "--workplace", str(Path(tmp) / "documented-batch-workplace"), "--apply")
    fixture.pf("project-context-refresh", "--project-root", str(project))
    for args in commands:
        index = args.index("--project-root") + 1
        assert args[index] == "."
        args[index] = str(project)
        print("RUN published example:", args[0], flush=True)
        fixture.pf(*args)
    run = core.load_run(project, "release-prep")
    assert run["status"] == "completed", run
    assert len(run["tasks"]) == 2 and all(task["status"] == "done" for task in run["tasks"]), run
    print("PASS: published compatibility example completes both tasks and the run")
