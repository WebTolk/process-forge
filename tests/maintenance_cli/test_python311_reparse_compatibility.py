"""Pure metadata regressions; no real fixtures, junctions or cleanup operations."""

from __future__ import annotations

import ast
import errno
import stat
import unittest
from collections.abc import Callable, Mapping
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import cast

from processforge_core.accounting.composition import WorkplaceAccounting
from processforge_core.accounting.storage import AccountingStorageError
from processforge_core.maintenance.contracts import MaintenanceError
from processforge_core.maintenance.journals import _failure_code, _safe_path

ROOT = Path(__file__).resolve().parents[2]
DATABASE = "/workplace/data/accounting/accounting.sqlite3"
ACCOUNTING_PATHS = (
    "/workplace/data",
    "/workplace/data/accounting",
    DATABASE,
    "/workplace/data/accounting/identity.json",
    "/workplace/data/accounting/projects",
)


class MetadataPath:
    """Supply only lstat metadata and lexical navigation, without Path APIs."""

    def __init__(
        self,
        name: str,
        entries: Mapping[str, SimpleNamespace | OSError],
        reads: list[str],
    ) -> None:
        self.name, self.entries, self.reads = name, entries, reads

    def __truediv__(self, name: str) -> MetadataPath:
        return MetadataPath(self.name + "/" + name, self.entries, self.reads)

    @property
    def parents(self) -> tuple[MetadataPath, ...]:
        return tuple(
            MetadataPath(str(parent), self.entries, self.reads)
            for parent in PurePosixPath(self.name).parents
        )

    def lstat(self) -> SimpleNamespace:
        self.reads.append(self.name)
        value = self.entries.get(self.name, SimpleNamespace(st_mode=stat.S_IFDIR))
        if isinstance(value, OSError):
            raise value
        return value


def guards(
    entries: Mapping[str, SimpleNamespace | OSError], reads: list[str]
) -> tuple[tuple[Callable[[], None], type[Exception], str], ...]:
    workplace = MetadataPath("/workplace", entries, reads)
    accounting = WorkplaceAccounting(
        workplace=cast(Path, workplace),
        project_root=Path("model-project"),
        project_id="model-project",
    )
    path = cast(Path, MetadataPath(DATABASE, entries, reads))
    return (
        (lambda: _safe_path(path), MaintenanceError, "migration_unsafe_path"),
        (accounting._safe_paths, AccountingStorageError, "accounting_unsafe_path"),
    )


class MetadataSafetyTests(unittest.TestCase):
    """Exercise the genuine Core functions with no filesystem-capable inputs."""

    def test_guards_accept_a_model_without_the_junction_api(self) -> None:
        self.assertFalse(hasattr(MetadataPath, "is_junction"))
        for guard, _error, _code in guards({}, []):
            guard()

    def test_regular_paths_with_and_without_windows_attributes(self) -> None:
        for attributes in (None, 0, 0x20):
            info = SimpleNamespace(st_mode=stat.S_IFREG)
            if attributes is not None:
                info.st_file_attributes = attributes
            for guard, _error, _code in guards({DATABASE: info}, []):
                with self.subTest(attributes=attributes, guard=guard):
                    guard()

    def test_every_existing_accounting_location_is_checked(self) -> None:
        reads: list[str] = []
        guards({}, reads)[1][0]()
        self.assertEqual(tuple(reads), ACCOUNTING_PATHS)

    def test_journal_checks_leaf_and_every_ancestor(self) -> None:
        reads: list[str] = []
        guards({}, reads)[0][0]()
        self.assertEqual(reads, [DATABASE, *map(str, PurePosixPath(DATABASE).parents)])

    def test_symlinks_are_rejected_at_each_accounting_location(self) -> None:
        for path in ACCOUNTING_PATHS:
            entries = {path: SimpleNamespace(st_mode=stat.S_IFLNK)}
            for guard, error, code in guards(entries, []):
                # Journals checks its selected path and its ancestors only.
                if code == "migration_unsafe_path" and path not in (
                    DATABASE,
                    *map(str, PurePosixPath(DATABASE).parents),
                ):
                    continue
                with self.subTest(path=path, code=code):
                    with self.assertRaisesRegex(error, "^" + code + "$"):
                        guard()

    def test_junction_and_other_reparse_tags_are_rejected(self) -> None:
        for path in ACCOUNTING_PATHS:
            for tag in (0xA0000003, 0xA000000C, 0x80000000):
                info = SimpleNamespace(
                    st_mode=stat.S_IFDIR,
                    st_file_attributes=0x400,
                    st_reparse_tag=tag,
                )
                guard, error, code = guards({path: info}, [])[1]
                with self.subTest(path=path, tag=tag):
                    with self.assertRaisesRegex(error, "^" + code + "$"):
                        guard()
        for path in (DATABASE, *map(str, PurePosixPath(DATABASE).parents)):
            info = SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x420)
            with self.subTest(journal_path=path):
                with self.assertRaisesRegex(
                    MaintenanceError, "^migration_unsafe_path$"
                ):
                    guards({path: info}, [])[0][0]()

    def test_missing_paths_do_not_block_creation(self) -> None:
        entries = {
            path: FileNotFoundError(errno.ENOENT, "model") for path in ACCOUNTING_PATHS
        }
        for guard, _error, _code in guards(entries, []):
            guard()

    def test_missing_leaf_does_not_hide_redirected_parent(self) -> None:
        entries: dict[str, SimpleNamespace | OSError] = {
            DATABASE: FileNotFoundError(errno.ENOENT, "model"),
            "/workplace/data": SimpleNamespace(
                st_mode=stat.S_IFDIR, st_file_attributes=0x400
            ),
        }
        for guard, error, code in guards(entries, []):
            with self.assertRaisesRegex(error, "^" + code + "$"):
                guard()

    def test_metadata_errors_propagate_without_allowing_access(self) -> None:
        for failure in (
            PermissionError(errno.EACCES, "model"),
            OSError(errno.EIO, "model"),
            NotADirectoryError(errno.ENOTDIR, "model"),
        ):
            for path in ACCOUNTING_PATHS:
                guard, _error, _code = guards({path: failure}, [])[1]
                with self.subTest(path=path, error=type(failure).__name__):
                    with self.assertRaises(type(failure)) as caught:
                        guard()
                    self.assertIs(caught.exception, failure)
            for path in (DATABASE, *map(str, PurePosixPath(DATABASE).parents)):
                with self.subTest(journal_path=path, error=type(failure).__name__):
                    with self.assertRaises(type(failure)) as caught:
                        guards({path: failure}, [])[0][0]()
                    self.assertIs(caught.exception, failure)
                    self.assertEqual(
                        _failure_code(caught.exception), "migration_io_failed"
                    )


def redirected_helper(relative: str) -> Callable[[Path], bool]:
    """Load only the pure existing helper, without importing held fixture suites."""
    tree = ast.parse((ROOT / relative).read_bytes(), filename=relative)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_redirected"
    )
    module = ast.Module(body=[function], type_ignores=[])
    namespace = {"Path": Path, "stat": stat}
    exec(compile(module, relative, "exec"), namespace)
    return cast(Callable[[Path], bool], namespace["_redirected"])


class ExistingHelperTests(unittest.TestCase):
    """Check the two pure distribution guards without invoking any fixtures."""

    def test_redirected_helpers_reject_links_and_reparse_metadata(self) -> None:
        for relative in (
            "tests/core_properties/test_composition.py",
            "tests/execution_migration/test_cold_handoff.py",
        ):
            helper = redirected_helper(relative)
            for info, expected in (
                (SimpleNamespace(st_mode=stat.S_IFREG), False),
                (SimpleNamespace(st_mode=stat.S_IFLNK), True),
                (SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400), True),
            ):
                with self.subTest(helper=relative, expected=expected):
                    path = cast(Path, MetadataPath("model", {"model": info}, []))
                    self.assertEqual(helper(path), expected)
            for failure in (FileNotFoundError("model"), PermissionError("model")):
                with self.subTest(helper=relative, error=type(failure).__name__):
                    path = cast(Path, MetadataPath("model", {"model": failure}, []))
                    with self.assertRaises(type(failure)):
                        helper(path)

    def test_cleanup_guard_precedes_only_modeled_removal(self) -> None:
        relative = "tests/maintenance_cli/test_journal_maintenance.py"
        tree = ast.parse((ROOT / relative).read_bytes(), filename=relative)
        fixture = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "MaintenanceFixture"
        )
        function = next(
            node
            for node in fixture.body
            if isinstance(node, ast.FunctionDef) and node.name == "cleanup_scratch"
        )
        owner = object()
        removed: list[object] = []
        namespace = {
            "stat": stat,
            "SCRATCH": SimpleNamespace(resolve=lambda: owner),
            "shutil": SimpleNamespace(rmtree=removed.append),
        }
        exec(
            compile(ast.Module(body=[function], type_ignores=[]), relative, "exec"),
            namespace,
        )
        cleanup = cast(Callable[[SimpleNamespace], None], namespace["cleanup_scratch"])
        for info, refused in (
            (SimpleNamespace(st_mode=stat.S_IFDIR), False),
            (SimpleNamespace(st_mode=stat.S_IFLNK), True),
            (SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400), True),
        ):
            root = SimpleNamespace(parent=owner, lstat=lambda: info)
            model = SimpleNamespace(
                root=root, assertEqual=self.assertEqual, assertFalse=self.assertFalse
            )
            removed.clear()
            with self.subTest(refused=refused, mode=info.st_mode):
                if refused:
                    with self.assertRaises(AssertionError):
                        cleanup(model)
                    self.assertEqual(removed, [])
                else:
                    cleanup(model)
                    self.assertEqual(removed, [root])
        for failure in (FileNotFoundError("model"), PermissionError("model")):
            removed.clear()
            root = SimpleNamespace(
                parent=owner, lstat=MetadataPath("model", {"model": failure}, []).lstat
            )
            model.root = root
            with self.assertRaises(type(failure)):
                cleanup(model)
            self.assertEqual(removed, [])
        model.root = SimpleNamespace(parent=object(), lstat=lambda: info)
        with self.assertRaises(AssertionError):
            cleanup(model)
        self.assertEqual(removed, [])

    def test_junction_assertion_stays_specific_to_mount_points(self) -> None:
        relative = "tests/maintenance_integration/test_acceptance.py"
        tree = ast.parse((ROOT / relative).read_bytes(), filename=relative)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name
            == "test_windows_junctions_are_refused_by_all_maintenance_operations"
        )
        assertion = next(
            node
            for node in function.body
            if isinstance(node, ast.Assert) and "st_reparse_tag" in ast.unparse(node)
        )
        expression = compile(ast.Expression(body=assertion.test), relative, "eval")
        for tag, expected in ((0xA0000003, True), (0xA000000C, False)):
            junction = SimpleNamespace(
                lstat=lambda: SimpleNamespace(st_reparse_tag=tag)
            )
            self.assertEqual(
                eval(expression, {"junction": junction, "stat": stat}), expected
            )
