"""Register existing CLI commands for evolution."""

from __future__ import annotations

import argparse
from collections.abc import Callable


class EvolutionCommandParser:
    """Register the existing evolution command family."""

    def __init__(
        self,
        *,
        evolve_candidate_create: Callable[[argparse.Namespace], int],
        evolve_candidate_export: Callable[[argparse.Namespace], int],
        evolve_candidate_list: Callable[[argparse.Namespace], int],
        evolve_candidate_sanitize: Callable[[argparse.Namespace], int],
        evolve_run: Callable[[argparse.Namespace], int],
    ) -> None:
        self._evolve_candidate_create = evolve_candidate_create
        self._evolve_candidate_export = evolve_candidate_export
        self._evolve_candidate_list = evolve_candidate_list
        self._evolve_candidate_sanitize = evolve_candidate_sanitize
        self._evolve_run = evolve_run

    def register(
        self, add_parser: Callable[..., argparse.ArgumentParser]
    ) -> None:
        evolve_run = add_parser("evolve-run", help="Create a run evolution report and optionally queue candidate files.")
        evolve_run.add_argument("--project-root", required=True, help="Project root path.")
        evolve_run.add_argument("--workplace", help="Workplace root path for durable learning queue.")
        evolve_run.add_argument("--process", default="task-batch-execution", help="Process id or YAML path.")
        evolve_run.add_argument("--run", required=True, help="Run id.")
        evolve_run.add_argument("--candidate-file", action="append", default=[], help="Candidate YAML file to queue. Repeatable.")
        evolve_run.set_defaults(func=self._evolve_run)

        evolve_candidate_create = add_parser("evolve-candidate-create", help="Queue a sanitized evolve candidate in a workplace learning queue.")
        evolve_candidate_create.add_argument("--project-root", required=True, help="Project root path for relative candidate paths.")
        evolve_candidate_create.add_argument("--workplace", required=True, help="Workplace root path.")
        evolve_candidate_create.add_argument("--from-file", required=True, help="Knowledge candidate YAML file.")
        evolve_candidate_create.set_defaults(func=self._evolve_candidate_create)

        evolve_candidate_list = add_parser("evolve-candidate-list", help="List workplace learning queue candidates.")
        evolve_candidate_list.add_argument("--workplace", required=True, help="Workplace root path.")
        evolve_candidate_list.set_defaults(func=self._evolve_candidate_list)

        evolve_candidate_export = add_parser("evolve-candidate-export", help="Export sanitized queued candidates to a learning bundle.")
        evolve_candidate_export.add_argument("--workplace", required=True, help="Workplace root path.")
        evolve_candidate_export.add_argument("--target", required=True, help="Target package id, for example docs.example.")
        evolve_candidate_export.add_argument("--output", required=True, help="Output bundle zip path.")
        evolve_candidate_export.set_defaults(func=self._evolve_candidate_export)

        evolve_candidate_sanitize = add_parser("evolve-candidate-sanitize", help="Write a sanitized copy of a knowledge candidate.")
        evolve_candidate_sanitize.add_argument("--file", required=True, help="Candidate YAML file.")
        evolve_candidate_sanitize.set_defaults(func=self._evolve_candidate_sanitize)
