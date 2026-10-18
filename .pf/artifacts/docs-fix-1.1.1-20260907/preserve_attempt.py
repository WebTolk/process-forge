"""Preserve bounded worker evidence before an explicit retry."""
import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser()
parser.add_argument("task")
parser.add_argument("attempt", type=int)
args = parser.parse_args()
if not args.task.startswith("docs111-") or "/" in args.task or "\\" in args.task or args.attempt < 1:
    parser.error("unexpected task or attempt")
destination = Path(__file__).parent / "attempts" / args.task / str(args.attempt)
destination.mkdir(parents=True, exist_ok=False)
source = ROOT / ".pf/runtime/agent-runs/docs-fix-1-1-1-shell-20260907" / args.task
for name in ("command.json", "exit.json", "status.json", "process.json", "stderr.log", "stdout.log"):
    if (source / name).is_file():
        shutil.copy2(source / name, destination / name)
report = Path(__file__).with_name(args.task + "-report.md")
if report.is_file():
    shutil.copy2(report, destination / "report.md")
print(destination.relative_to(ROOT).as_posix())
