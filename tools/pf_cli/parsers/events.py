"""Register existing CLI commands for events."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Collection


class HookCommandParser:
    """Register the existing hooks command family."""

    def __init__(
        self,
        *,
        events_validate: Callable[[argparse.Namespace], int],
        hooks_dispatch: Callable[[argparse.Namespace], int],
        event_types: Collection[str],
    ) -> None:
        self._events_validate = events_validate
        self._hooks_dispatch = hooks_dispatch
        self._event_types = event_types

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        hooks_dispatch = add_parser("hooks-dispatch", help="Dry-run or enqueue hook delivery for a ProcessForge event.")
        hooks_dispatch.add_argument("--project-root", required=True, help="Project root path.")
        hooks_dispatch.add_argument("--event-type", required=True, choices=self._event_types, help="Event type to test or enqueue.")
        hooks_dispatch.add_argument("--severity", default="info", choices=["info", "warn", "error"], help="Event severity.")
        hooks_dispatch.add_argument("--session-id", help="Optional session id.")
        hooks_dispatch.add_argument("--assignment-id", help="Optional assignment id.")
        hooks_dispatch.add_argument("--dry-run", action="store_true", help="Report selected hooks without writing event/outbox payloads.")
        hooks_dispatch.add_argument("--outbox", action="store_true", help="Write matching hook payloads to .pf/runtime/hooks/outbox/.")
        hooks_dispatch.add_argument("--send", action="store_true", help="Reserved future network transport; disabled by default.")
        hooks_dispatch.add_argument("--since", help="Optional timestamp or event id marker for future event replay.")
        hooks_dispatch.set_defaults(func=self._hooks_dispatch)

        events_validate = add_parser("events-validate", help="Validate runtime event and chat NDJSON files.")
        events_validate.add_argument("--project-root", required=True, help="Project root path.")
        events_validate.set_defaults(func=self._events_validate)


class ChatCommandParser:
    """Register the existing chat command family."""

    def __init__(
        self,
        *,
        chat_export: Callable[[argparse.Namespace], int],
        chat_record: Callable[[argparse.Namespace], int],
    ) -> None:
        self._chat_export = chat_export
        self._chat_record = chat_record

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        chat_record = add_parser("chat-record", help="Record one chat message into the private transcript and emit a chat event.")
        chat_record.add_argument("--project-root", required=True, help="Project root path.")
        chat_record.add_argument("--session-id", required=True, help="Session id.")
        chat_record.add_argument("--participant", required=True, help="Participant id, for example operator or subagent-reviewer-1.")
        chat_record.add_argument("--participant-type", choices=["human", "agent", "subagent", "tool"], help="Participant type.")
        chat_record.add_argument("--participant-role", help="Participant role; defaults to participant id.")
        chat_record.add_argument("--role", required=True, choices=["user", "assistant", "system", "tool", "subagent"], help="Message role.")
        chat_record.add_argument("--content", help="Message content.")
        chat_record.add_argument("--content-file", help="Read message content from a UTF-8 text file.")
        chat_record.add_argument("--turn-id", help="Optional turn id.")
        chat_record.add_argument("--parent-message-id", help="Optional parent message id.")
        chat_record.add_argument("--process-id", help="Optional process id.")
        chat_record.add_argument("--stage-id", help="Optional stage id.")
        chat_record.add_argument("--assignment-id", help="Optional assignment id.")
        chat_record.add_argument("--include-content", action="store_true", help="Opt in to include redacted content in the emitted event.")
        chat_record.set_defaults(func=self._chat_record)

        chat_export = add_parser("chat-export", help="Export a chat transcript to an outbox payload without network send.")
        chat_export.add_argument("--project-root", required=True, help="Project root path.")
        chat_export.add_argument("--session-id", required=True, help="Session id.")
        chat_export.add_argument("--target", required=True, choices=["wtaicc"], help="Outbox target.")
        chat_export.add_argument("--outbox", action="store_true", help="Write .pf/runtime/hooks/outbox/wtaicc payload.")
        chat_export.add_argument("--include-content", action="store_true", help="Opt in to include redacted transcript content in the outbox payload.")
        chat_export.set_defaults(func=self._chat_export)
