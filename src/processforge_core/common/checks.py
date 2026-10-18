"""Shared check values and construction."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Check:
    level: str
    message: str


def check(level: str, message: str) -> Check:
    return Check(level.upper(), message)
