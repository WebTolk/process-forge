"""Register existing CLI commands for distribution."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path


class DeliveryCommandParser:
    """Register the existing delivery command family."""

    def __init__(
        self,
        *,
        clean: Callable[[argparse.Namespace], int],
        dev_test: Callable[[argparse.Namespace], int],
        examples_check: Callable[[argparse.Namespace], int],
        release_archive_test: Callable[[argparse.Namespace], int],
        release_check: Callable[[argparse.Namespace], int],
        release_pack: Callable[[argparse.Namespace], int],
        release_test: Callable[[argparse.Namespace], int],
        version: Callable[[argparse.Namespace], int],
        distribution_root: Path,
    ) -> None:
        self._clean = clean
        self._dev_test = dev_test
        self._examples_check = examples_check
        self._release_archive_test = release_archive_test
        self._release_check = release_check
        self._release_pack = release_pack
        self._release_test = release_test
        self._version = version
        self._distribution_root = distribution_root

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        release_check = add_parser("release-check", help="Run MVP release hygiene checks.")
        release_check.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        release_check.set_defaults(func=self._release_check)

        release_test = add_parser("release-test", help="Run the release validation suite.")
        release_test.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        release_test.add_argument("--public", action="store_true", help="Apply public-release gates in addition to development release checks.")
        release_test.add_argument("--list", action="store_true", help="List release-test check names without running them.")
        release_test.add_argument("--only", action="append", default=[], help="Run only a named check. Repeatable.")
        release_test.add_argument("--skip", action="append", default=[], help="Skip a named check. Repeatable.")
        release_test.add_argument("--fail-fast", action="store_true", help="Stop after the first failed check.")
        release_test.add_argument("--timeout-scale", type=float, default=1.0, help="Multiply per-check timeouts by this finite positive value.")
        release_test.add_argument("--trace-smokes", action="store_true", help="Write a per-smoke trace report with elapsed and timeout diagnostics.")
        release_test.add_argument("--no-clean", action="store_true", help="Do not run the clean release artifacts check.")
        release_test.add_argument("--clean-first", action="store_true", help="Run clean release artifacts before checks. Default unless --no-clean is set.")
        release_test.set_defaults(func=self._release_test)

        smoke_all = add_parser("smoke-all", help="Alias for release-test.")
        smoke_all.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        smoke_all.add_argument("--public", action="store_true", help="Apply public-release gates in addition to development release checks.")
        smoke_all.add_argument("--list", action="store_true", help="List release-test check names without running them.")
        smoke_all.add_argument("--only", action="append", default=[], help="Run only a named check. Repeatable.")
        smoke_all.add_argument("--skip", action="append", default=[], help="Skip a named check. Repeatable.")
        smoke_all.add_argument("--fail-fast", action="store_true", help="Stop after the first failed check.")
        smoke_all.add_argument("--timeout-scale", type=float, default=1.0, help="Multiply per-check timeouts by this finite positive value.")
        smoke_all.add_argument("--trace-smokes", action="store_true", help="Write a per-smoke trace report with elapsed and timeout diagnostics.")
        smoke_all.add_argument("--no-clean", action="store_true", help="Do not run the clean release artifacts check.")
        smoke_all.add_argument("--clean-first", action="store_true", help="Run clean release artifacts before checks. Default unless --no-clean is set.")
        smoke_all.set_defaults(func=self._release_test)

        dev_test = add_parser("dev-test", help="Run project-local dogfooding tests from .pf/dogfooding.")
        dev_test.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        dev_test.add_argument("--list", action="store_true", help="List dogfooding suites and tests.")
        dev_test.add_argument("--suite", action="append", default=[], help="Dogfooding suite id to run. Repeatable.")
        dev_test.add_argument("--test", action="append", default=[], help="Dogfooding test id to run. Repeatable.")
        dev_test.add_argument("--fail-fast", action="store_true", help="Stop after the first failed dogfooding test.")
        dev_test.add_argument("--timeout-scale", type=float, default=1.0, help="Multiply dogfooding test timeouts by this finite positive value.")
        dev_test.set_defaults(func=self._dev_test)

        dogfood_test = add_parser("dogfood-test", help="Alias for dev-test.")
        dogfood_test.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        dogfood_test.add_argument("--list", action="store_true", help="List dogfooding suites and tests.")
        dogfood_test.add_argument("--suite", action="append", default=[], help="Dogfooding suite id to run. Repeatable.")
        dogfood_test.add_argument("--test", action="append", default=[], help="Dogfooding test id to run. Repeatable.")
        dogfood_test.add_argument("--fail-fast", action="store_true", help="Stop after the first failed dogfooding test.")
        dogfood_test.add_argument("--timeout-scale", type=float, default=1.0, help="Multiply dogfooding test timeouts by this finite positive value.")
        dogfood_test.set_defaults(func=self._dev_test)

        clean = add_parser("clean", help="Remove safe generated ProcessForge artifacts.")
        clean.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        clean.add_argument("--release", action="store_true", help="Remove safe generated release artifacts.")
        clean.set_defaults(func=self._clean)

        release_pack = add_parser("release-pack", help="Build a portable ProcessForge release archive and manifest.")
        release_pack.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        release_pack.add_argument("--output", required=True, help="Release archive path.")
        release_pack.add_argument("--dry-run", action="store_true", help="Print archive contents without writing files.")
        release_pack.set_defaults(func=self._release_pack)

        release_archive_test = add_parser("release-archive-test", help="Inspect a release archive and run release-test after extraction.")
        release_archive_test.add_argument("--archive", required=True, help="Release archive ZIP path.")
        release_archive_test.add_argument("--manifest", help="Optional release manifest path. Defaults to archive path with .manifest.json suffix.")
        release_archive_test.add_argument("--root", help="Optional source root; when set, verify archive entries and manifest hashes are current.")
        release_archive_test.add_argument("--extracted-test", choices=["full", "quick", "skip"], default="full", help="How much release-test coverage to run inside the extracted archive. Default: full.")
        release_archive_test.add_argument("--timeout-scale", type=float, default=1.0, help="Pass this finite positive scale to the extracted release-test and multiply the outer process timeout by it.")
        release_archive_test.set_defaults(func=self._release_archive_test)

        examples_check = add_parser("examples-check", help="Validate release examples for portability and stale generated data.")
        examples_check.add_argument("--root", default=str(self._distribution_root), help="ProcessForge root path.")
        examples_check.set_defaults(func=self._examples_check)

        version = add_parser("version", help="Print ProcessForge distribution and spec versions.")
        version.set_defaults(func=self._version)


class CoreUpdateCommandParser:
    """Register the existing core update command family."""

    def __init__(
        self,
        *,
        core_update_apply: Callable[[argparse.Namespace], int],
        core_update_plan: Callable[[argparse.Namespace], int],
        core_update_repair: Callable[[argparse.Namespace], int],
        core_update_status: Callable[[argparse.Namespace], int],
    ) -> None:
        self._core_update_apply = core_update_apply
        self._core_update_plan = core_update_plan
        self._core_update_repair = core_update_repair
        self._core_update_status = core_update_status

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        core_update = add_parser("core-update", help="Plan and apply manifest-based ProcessForge core archive updates.")
        core_update_sub = core_update.add_subparsers(dest="core_update_command", required=True)
        core_update_status = core_update_sub.add_parser("status", help="Read installed core manifest and incomplete update state.")
        core_update_status.add_argument("--core-root", required=True, help="Installed ProcessForge core root.")
        core_update_status.set_defaults(func=self._core_update_status)
        core_update_plan = core_update_sub.add_parser("plan", help="Validate an archive and print add/change/remove plan without modifying files.")
        core_update_plan.add_argument("--core-root", required=True, help="Installed ProcessForge core root.")
        core_update_plan.add_argument("--archive", required=True, help="ProcessForge release archive containing processforge-core.manifest.json.")
        core_update_plan.add_argument("--workplace-root", help="Existing Workplace to assess for compatible archive-declared migration.")
        core_update_plan.set_defaults(func=self._core_update_plan)
        core_update_apply = core_update_sub.add_parser("apply", help="Apply a manifest-based core update from an explicit archive.")
        core_update_apply.add_argument("--core-root", required=True, help="Installed ProcessForge core root.")
        core_update_apply.add_argument("--archive", required=True, help="ProcessForge release archive containing processforge-core.manifest.json.")
        core_update_apply.add_argument("--workplace-root", help="Existing Workplace to migrate with the Core update.")
        core_update_apply.add_argument("--confirm", action="store_true", help="Required confirmation for file changes.")
        core_update_apply.add_argument("--force-local-modifications", action="store_true", help="Allow replacing locally modified PF-owned files after backup.")
        core_update_apply.set_defaults(func=self._core_update_apply)
        core_update_repair = core_update_sub.add_parser("repair", help="Inspect incomplete core update repair state.")
        core_update_repair.add_argument("--core-root", required=True, help="Installed ProcessForge core root.")
        core_update_repair.set_defaults(func=self._core_update_repair)
