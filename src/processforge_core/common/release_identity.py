"""Canonical release identity values and manifest digest format."""

import re

RELEASE_NAME = "processforge"
RELEASE_ARCHIVE_VERSION = "1.3.0-alpha3"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
