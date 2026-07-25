#!/usr/bin/env python3
"""Run project-local ProcessForge dogfooding smoke tests."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).resolve().parent / "tests" / "manifest.yaml"


@dataclass(frozen=True)
class DogfoodingTest:
    name: str
    script: Path
    timeout_seconds: int
    layer: str


def load_manifest() -> dict[str, Any]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: invalid dogfooding manifest: {MANIFEST}")
    return data


def resolve_tests(data: dict[str, Any], suites: list[str], tests: list[str]) -> list[DogfoodingTest]:
    manifest_tests = data.get("tests")
    manifest_suites = data.get("suites")
    if not isinstance(manifest_tests, dict) or not isinstance(manifest_suites, dict):
        raise SystemExit("FAIL: dogfooding manifest must contain suites and tests maps")
    selected: list[str] = []
    for suite in suites:
        suite_data = manifest_suites.get(suite)
        if not isinstance(suite_data, dict) or not isinstance(suite_data.get("tests"), list):
            raise SystemExit(f"FAIL: unknown dogfooding suite: {suite}")
        selected.extend(str(item) for item in suite_data["tests"])
    selected.extend(tests)
    if not selected:
        selected = sorted(manifest_tests)
    resolved: list[DogfoodingTest] = []
    seen: set[str] = set()
    for name in selected:
        if name in seen:
            continue
        seen.add(name)
        test_data = manifest_tests.get(name)
        if not isinstance(test_data, dict):
            raise SystemExit(f"FAIL: unknown dogfooding test: {name}")
        script = MANIFEST.parent / str(test_data.get("script", ""))
        resolved.append(
            DogfoodingTest(
                name=name,
                script=script.resolve(),
                timeout_seconds=int(test_data.get("timeout_seconds", 180)),
                layer=str(test_data.get("layer", "dogfooding")),
            )
        )
    return resolved


def list_tests(data: dict[str, Any]) -> int:
    suites = data.get("suites", {})
    tests = data.get("tests", {})
    print("Dogfooding suites:")
    for name, suite_data in sorted(suites.items()):
        suite_tests = suite_data.get("tests", []) if isinstance(suite_data, dict) else []
        print(f"- {name}: {len(suite_tests)} tests")
    print("Dogfooding tests:")
    for name, test_data in sorted(tests.items()):
        script = test_data.get("script", "") if isinstance(test_data, dict) else ""
        layer = test_data.get("layer", "dogfooding") if isinstance(test_data, dict) else "dogfooding"
        print(f"- {name}\tlayer={layer}\tscript={script}")
    return 0


def run_test(test: DogfoodingTest, timeout_scale: float) -> bool:
    if not test.script.is_file():
        print(f"FAIL {test.name}: missing script {test.script}")
        return False
    timeout = max(1, int(test.timeout_seconds * timeout_scale))
    env = os.environ.copy()
    env["PF_REPO_ROOT"] = str(ROOT)
    started = time.perf_counter()
    print(f"RUN {test.name}: layer={test.layer} timeout={timeout}s")
    try:
        result = subprocess.run(
            [sys.executable, str(test.script)],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - started
        print(f"FAIL {test.name}: timeout after {timeout}s elapsed={elapsed:.2f}s")
        output = "\n".join(part for part in [exc.stdout, exc.stderr] if isinstance(part, str))
        for line in output.splitlines()[-40:]:
            print(f"  {line}")
        return False
    elapsed = time.perf_counter() - started
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.returncode == 0:
        print(f"PASS {test.name}: elapsed={elapsed:.2f}s")
        return True
    print(f"FAIL {test.name}: exit={result.returncode} elapsed={elapsed:.2f}s")
    for line in output.splitlines()[-40:]:
        print(f"  {line}")
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="list dogfooding suites and tests")
    parser.add_argument("--suite", action="append", default=[], help="suite id to run")
    parser.add_argument("--test", action="append", default=[], help="single test id to run")
    parser.add_argument("--fail-fast", action="store_true", help="stop on the first failing test")
    parser.add_argument("--timeout-scale", type=float, default=1.0, help="multiply per-test timeouts")
    args = parser.parse_args()
    if args.timeout_scale <= 0:
        print("FAIL: --timeout-scale must be greater than 0")
        return 1
    data = load_manifest()
    if args.list:
        return list_tests(data)
    selected = resolve_tests(data, args.suite, args.test)
    failed = False
    for test in selected:
        ok = run_test(test, args.timeout_scale)
        failed = failed or not ok
        if failed and args.fail_fast:
            break
    print("RESULT: FAIL" if failed else "RESULT: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
