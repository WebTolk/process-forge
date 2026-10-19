"""Canonical release identity values and manifest digest format."""

import re


RELEASE_NAME = "processforge"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
