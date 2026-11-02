"""Record existing process events and coordinate mandatory hook dispatch."""

from __future__ import annotations

import sqlite3
import sys
from contextlib import ExitStack
from contextvars import ContextVar, Token
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..maintenance.storage_migration import StorageMigrationHost

from ..configuration import ConfigurationProvider, PFConfig
from ..database import DatabaseFactory
from ..process_event_journal import ProcessEventJournal
from ..project.configuration_inputs import (
    ProjectConfigurationReader,
    operation_device_path,
    operation_storage_host,
    project_configuration_reader,
)
from ..runtime.execution_admission import ExecutionAdmission
from ..sqlite_storage import JournalError
from ..work.consistency import RunTaskInputReader
from .hook_dispatch import RuntimeHookDispatcher
from .hook_policy import HookDispatchPolicy
from .telemetry import TelemetryEventService


class ProcessEventRecorder:
    def __init__(
        self,
        *,
        journal: ProcessEventJournal | None = None,
        inputs: RunTaskInputReader | None = None,
        hooks: HookDispatchPolicy | None = None,
        telemetry: TelemetryEventService | None = None,
        configuration: ProjectConfigurationReader | ConfigurationProvider | None = None,
        dispatcher: RuntimeHookDispatcher | None = None,
        storage_host: StorageMigrationHost | None = None,
    ) -> None:
        self.journal = (
            journal
            if journal is not None
            else ProcessEventJournal(storage_host=storage_host)
        )
        self.inputs = inputs if inputs is not None else RunTaskInputReader()
        if hooks is None:
            hooks = (
                dispatcher.policy if dispatcher is not None else HookDispatchPolicy()
            )
        self.hooks = hooks
        self.telemetry = telemetry if telemetry is not None else TelemetryEventService()
        self.configuration = (
            configuration if configuration is not None else project_configuration_reader
        )
        self.dispatcher = (
            dispatcher
            if dispatcher is not None
            else RuntimeHookDispatcher(policy=self.hooks)
        )

    def admit_process_event(
        self,
        project_root: Path,
        event: dict[str, Any],
        *,
        dispatch: bool = True,
        workplace_root: Path | None = None,
    ) -> bool:
        if not (event.get("event_id") or event.get("id")):
            raise JournalError("journal_event_id_required")
        active = _PUBLICATION.get()
        if (
            active is not None
            and active.recorder is self
            and active.project_root == project_root
        ):
            return active.append(event, dispatch=dispatch)
        events_path, config, journal = self._event_journal(project_root, workplace_root)
        inserted = journal.append(
            events_path,
            event,
            event_id_value=self.hooks.event_id_value,
            record=config.logging.events,
            queue_dispatch=dispatch
            and bool(self.hooks.selected_hooks(project_root, event)),
        )
        if dispatch:
            for pending in journal.pending_dispatch(
                events_path, event_id=self.hooks.event_id_value(event)
            ):
                self.dispatcher.dispatch_hooks(
                    project_root, pending, dry_run=False, outbox=True
                )
                journal.complete_dispatch(
                    events_path, self.hooks.event_id_value(pending)
                )
        return inserted

    def _event_journal(
        self, project_root: Path, workplace_root: Path | None = None
    ) -> tuple[Path, PFConfig, ProcessEventJournal]:
        events_path, _outbox = self.inputs.event_runtime_paths(project_root)
        config = (
            self.configuration.current()
            if isinstance(self.configuration, ConfigurationProvider)
            else self.configuration.project_configuration(
                project_root, workplace_root
            ).config
        )
        journal = self.journal
        if type(journal) is ProcessEventJournal and journal.storage_host is None:
            from ..composition import build_storage_migration_host
            from ..project.metadata import ProjectMetadataReader

            metadata = ProjectMetadataReader(project_root)
            declared = metadata.workplace_manifest()
            owner = metadata.manifest().get("project")
            if isinstance(owner, dict) and owner.get("id"):
                pinned = ConfigurationProvider.pinned(config)
                selected_workplace = workplace_root or (
                    declared.parent if declared else None
                )
                host = operation_storage_host(events_path.with_name("events.sqlite3"))
                host = host or build_storage_migration_host(
                    project_root=project_root,
                    workplace_root=selected_workplace,
                    device_config_path=operation_device_path(
                        project_root,
                        selected_workplace,
                        self.configuration.device_path
                        if isinstance(self.configuration, ConfigurationProvider)
                        else None,
                    ),
                    configuration=pinned,
                )
                journal = ProcessEventJournal(driver=journal.driver, storage_host=host)
        if type(journal) is ProcessEventJournal and journal.driver is None:
            journal = ProcessEventJournal(
                driver=DatabaseFactory.resolve_driver(config.database),
                storage_host=journal.storage_host,
            )
        return events_path, config, journal

    def publication(
        self, project_root: Path, workplace_root: Path | None, *, event_time: str
    ) -> ProcessEventPublication:
        """Preflight and retain one short journal admission for Work publication."""
        return ProcessEventPublication(self, project_root, workplace_root, event_time)

    def append_process_event(
        self,
        project_root: Path,
        event: dict[str, Any],
        *,
        dispatch: bool = True,
        workplace_root: Path | None = None,
    ) -> Path:
        events_path, _outbox = self.inputs.event_runtime_paths(project_root)
        self.admit_process_event(
            project_root, event, dispatch=dispatch, workplace_root=workplace_root
        )
        return events_path

    def emit_process_event(
        self, project_root: Path, event_type: str, **kwargs: Any
    ) -> dict[str, Any]:
        event = self.telemetry.processforge_event(project_root, event_type, **kwargs)
        active = _PUBLICATION.get()
        if (
            active is not None
            and active.recorder is self
            and active.project_root == project_root
        ):
            event["time"] = active.event_time
        self.append_process_event(project_root, event)
        return event


_PUBLICATION: ContextVar[ProcessEventPublication | None] = ContextVar(
    "pf_process_event_publication", default=None
)


class ProcessEventPublication:
    """One admitted SQL batch; dispatch only after its durable commit.

    Resource exits are not injected with frozen domain exceptions. SQL rollback
    is explicit, while the existing connection and gate owners close normally.
    State rendering and projections belong outside this short context.
    """

    def __init__(
        self,
        recorder: ProcessEventRecorder,
        project_root: Path,
        workplace_root: Path | None,
        event_time: str,
    ) -> None:
        self.recorder, self.project_root = recorder, project_root
        self.workplace_root, self.event_time = workplace_root, event_time
        self.stack = ExitStack()
        self.token: Token[ProcessEventPublication | None] | None = None
        self.connection: sqlite3.Connection | None = None
        self.pending: list[str] = []

    def __enter__(self) -> ProcessEventPublication:
        if _PUBLICATION.get() is not None:
            raise JournalError("journal_publication_nested")
        try:
            self.path, self.config, self.journal = self.recorder._event_journal(
                self.project_root, self.workplace_root
            )
            module = sys.modules.get("pf_native_control")
            current = getattr(module, "current_entry", None)
            entry = current() if callable(current) else None
            if entry is not None:
                self.stack.enter_context(entry.operation())
            self.stack.enter_context(
                ExecutionAdmission().start(self.project_root, self.workplace_root)
            )
            self.connection = self.stack.enter_context(
                self.journal.connection(
                    self.path,
                    writable=True,
                    driver=self.journal.driver,
                    storage_host=self.journal.storage_host,
                )
            )
            self.connection.execute("BEGIN IMMEDIATE")
            self.token = _PUBLICATION.set(self)
            return self
        except BaseException:
            self.stack.close()
            raise

    def append(self, event: dict[str, Any], *, dispatch: bool) -> bool:
        if self.connection is None:
            raise JournalError("journal_publication_inactive")
        inserted = self.journal._append(
            self.connection,
            event,
            self.recorder.hooks.event_id_value,
            self.config.logging.events,
            queue_dispatch=dispatch
            and bool(self.recorder.hooks.selected_hooks(self.project_root, event)),
        )
        if dispatch:
            self.pending.append(self.recorder.hooks.event_id_value(event))
        return inserted

    def __exit__(self, kind: Any, error: Any, traceback: Any) -> None:
        try:
            if self.token is not None:
                _PUBLICATION.reset(self.token)
            if self.connection is not None and self.connection.in_transaction:
                self.connection.execute("ROLLBACK" if kind is not None else "COMMIT")
        finally:
            self.stack.close()
        if kind is None:
            # The batch and its native/admission/identity gates have closed.
            # Dispatch uses existing idempotent event/delivery IDs and outbox.
            for event_id in self.pending:
                for pending in self.journal.pending_dispatch(
                    self.path, event_id=event_id
                ):
                    self.recorder.dispatcher.dispatch_hooks(
                        self.project_root, pending, dry_run=False, outbox=True
                    )
                    self.journal.complete_dispatch(
                        self.path, self.recorder.hooks.event_id_value(pending)
                    )
