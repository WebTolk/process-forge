"""Record existing process events and coordinate mandatory hook dispatch."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..maintenance.storage_migration import StorageMigrationHost

from ..configuration import ConfigurationProvider
from ..database import DatabaseFactory
from ..process_event_journal import ProcessEventJournal
from ..project.configuration_inputs import (
    ProjectConfigurationReader,
    project_configuration_reader,
)
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
        events_path, _outbox = self.inputs.event_runtime_paths(project_root)
        config = (
            self.configuration.current()
            if isinstance(self.configuration, ConfigurationProvider)
            else self.configuration.project_configuration(
                project_root, workplace_root
            ).config
        )
        journal = self.journal
        if type(journal) is ProcessEventJournal and journal.driver is None:
            journal = ProcessEventJournal(
                driver=DatabaseFactory.resolve_driver(config.database),
                storage_host=journal.storage_host,
            )
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
        self.append_process_event(project_root, event)
        return event
