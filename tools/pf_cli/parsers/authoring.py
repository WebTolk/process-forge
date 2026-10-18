"""Register existing CLI commands for authoring."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class ProcessAuthoringCommandParser:
    """Register the existing authoring command family."""

    def __init__(
        self,
        *,
        authoring_parity_check_all: Callable[[argparse.Namespace], int],
        authoring_transaction_recover: Callable[[argparse.Namespace], int],
        knowledge_package_parity_check: Callable[[argparse.Namespace], int],
        platform_parity_check: Callable[[argparse.Namespace], int],
        process_authoring_apply: Callable[[argparse.Namespace], int],
        process_authoring_import: Callable[[argparse.Namespace], int],
        process_authoring_review: Callable[[argparse.Namespace], int],
        process_authoring_start: Callable[[argparse.Namespace], int],
        process_create: Callable[[argparse.Namespace], int],
        process_parity_check: Callable[[argparse.Namespace], int],
        process_parity_check_all: Callable[[argparse.Namespace], int],
        template_parity_check: Callable[[argparse.Namespace], int],
    ) -> None:
        self._authoring_parity_check_all = authoring_parity_check_all
        self._authoring_transaction_recover = authoring_transaction_recover
        self._knowledge_package_parity_check = knowledge_package_parity_check
        self._platform_parity_check = platform_parity_check
        self._process_authoring_apply = process_authoring_apply
        self._process_authoring_import = process_authoring_import
        self._process_authoring_review = process_authoring_review
        self._process_authoring_start = process_authoring_start
        self._process_create = process_create
        self._process_parity_check = process_parity_check
        self._process_parity_check_all = process_parity_check_all
        self._template_parity_check = template_parity_check

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        process_authoring_start = add_parser("process-authoring-start", help="Start a guided process authoring session.")
        process_authoring_start.add_argument("--project-root", required=True, help="Project root path.")
        process_authoring_start.add_argument("--id", help="Process id.")
        process_authoring_start.add_argument("--title", help="Process title.")
        process_authoring_start.add_argument("--description", help="Process description.")
        process_authoring_start.add_argument("--scope", help="Optional process scope recorded in answers.")
        process_authoring_start.add_argument("--kind", help="Optional process kind recorded in answers.")
        process_authoring_start.add_argument("--answers", help="Optional process authoring answers YAML.")
        process_authoring_start.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        process_authoring_start.add_argument("--apply", action="store_true", help="Write authoring session files.")
        process_authoring_start.set_defaults(func=self._process_authoring_start)

        process_authoring_review = add_parser("process-authoring-review", help="Review a process authoring draft for structural logic issues.")
        process_authoring_review.add_argument("--project-root", required=True, help="Project root path.")
        process_authoring_review.add_argument("--process", required=True, help="Process id.")
        process_authoring_review.set_defaults(func=self._process_authoring_review)

        process_authoring_apply = add_parser("process-authoring-apply", help="Apply a reviewed process authoring draft.")
        process_authoring_apply.add_argument("--project-root", required=True, help="Project root path.")
        process_authoring_apply.add_argument("--process", required=True, help="Process id.")
        process_authoring_apply.add_argument("--output-root", choices=["user", "custom", "core"], help="Process root for generated process YAML. Defaults to user.")
        process_authoring_apply.add_argument("--core", action="store_true", help="Allow writing generated process YAML to processes/core.")
        process_authoring_apply.add_argument("--dry-run", action="store_true", help="Show the complete transaction plan without writing.")
        process_authoring_apply.add_argument("--apply", action="store_true", help="Apply the complete process authoring transaction.")
        process_authoring_apply.set_defaults(func=self._process_authoring_apply)

        process_authoring_import = add_parser("process-authoring-import", help="Backfill an authoring session from an existing process definition.")
        process_authoring_import.add_argument("--project-root", required=True, help="Project root path.")
        process_authoring_import.add_argument("--process", help="Process id.")
        process_authoring_import.add_argument("--process-file", help="Process YAML path.")
        process_authoring_import.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        process_authoring_import.add_argument("--apply", action="store_true", help="Write backfill files.")
        process_authoring_import.set_defaults(func=self._process_authoring_import)

        process_parity_check = add_parser("process-parity-check", help="Check semantic parity between a process and its authoring-import draft.")
        process_parity_check.add_argument("--project-root", required=True, help="Project root path.")
        process_parity_check.add_argument("--process", help="Process id.")
        process_parity_check.add_argument("--process-file", help="Process YAML path.")
        process_parity_check.add_argument("--candidate-file", help="Optional candidate YAML for diagnostics.")
        process_parity_check.set_defaults(func=self._process_parity_check)

        process_parity_check_all = add_parser("process-parity-check-all", help="Check semantic authoring parity for every process definition.")
        process_parity_check_all.add_argument("--project-root", required=True, help="Project root path.")
        process_parity_check_all.set_defaults(func=self._process_parity_check_all)

        template_parity_check = add_parser("template-parity-check", help="Check template authoring parity or record a SKIP reason.")
        template_parity_check.add_argument("--project-root", help="Project root path.")
        template_parity_check.add_argument("--workplace", help="Workplace root path; accepted for future discovery.")
        template_parity_check.add_argument("--template", required=True, help="Template id.")
        template_parity_check.set_defaults(func=self._template_parity_check)

        knowledge_package_parity_check = add_parser("knowledge-package-parity-check", help="Check knowledge package authoring parity or record a SKIP reason.")
        knowledge_package_parity_check.add_argument("--project-root", help="Project root path.")
        knowledge_package_parity_check.add_argument("--workplace", help="Workplace root path; accepted for future discovery.")
        knowledge_package_parity_check.add_argument("--package", required=True, help="Package id.")
        knowledge_package_parity_check.set_defaults(func=self._knowledge_package_parity_check)

        platform_parity_check = add_parser("platform-parity-check", help="Check platform contract authoring parity or record a SKIP reason.")
        platform_parity_check.add_argument("--project-root", help="Project root path.")
        platform_parity_check.add_argument("--workplace", help="Workplace root path; accepted for future discovery.")
        platform_parity_check.add_argument("--platform", required=True, help="Platform id.")
        platform_parity_check.set_defaults(func=self._platform_parity_check)

        authoring_parity_check_all = add_parser("authoring-parity-check-all", help="Run process and resource authoring parity checks.")
        authoring_parity_check_all.add_argument("--project-root", required=True, help="Project root path.")
        authoring_parity_check_all.set_defaults(func=self._authoring_parity_check_all)

        process_create = add_parser("process-create", help="Create a new process from answers in one command.")
        process_create.add_argument("--project-root", required=True, help="Project root path.")
        process_create.add_argument("--id", help="Process id when no answers file supplies one.")
        process_create.add_argument("--title", help="Process title when no answers file supplies one.")
        process_create.add_argument("--answers", help="Optional process authoring answers YAML.")
        process_create.add_argument("--output-root", choices=["user", "custom", "core"], help="Process root for generated process YAML. Defaults to user.")
        process_create.add_argument("--core", action="store_true", help="Allow writing generated process YAML to processes/core.")
        process_create.add_argument("--dry-run", action="store_true", help="Show planned files without writing.")
        process_create.add_argument("--apply", action="store_true", help="Write the process, prompt, docs, and example.")
        process_create.set_defaults(func=self._process_create)

        authoring_transaction_recover = add_parser("authoring-transaction-recover", help="Recover or replay an authoring transaction.")
        authoring_transaction_recover.add_argument("--runtime-root", required=True, help="Runtime root containing authoring-transactions.")
        authoring_transaction_recover.add_argument("--transaction", required=True, help="Transaction id.")
        authoring_transaction_recover.add_argument("--dry-run", action="store_true", help="Show current transaction recovery state without writing.")
        authoring_transaction_recover.add_argument("--apply", action="store_true", help="Recover rollback state or replay pending post-commit effects.")
        authoring_transaction_recover.set_defaults(func=self._authoring_transaction_recover)
