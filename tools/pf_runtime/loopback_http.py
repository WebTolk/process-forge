"""Direct HTTP transport for the local ProcessForge Runtime."""

from __future__ import annotations

import re
from collections.abc import Mapping
from contextlib import closing
from http.client import HTTPConnection, HTTPException
from urllib.parse import SplitResult, urlsplit

_LOOPBACK_HOST = "127.0.0.1"
_LOOPBACK_AUTHORITY = re.compile(r"127\.0\.0\.1:[0-9]+")
_INVALID_URL_CHAR = re.compile(r"[\x00-\x20\x7f#\\]")


class LoopbackTransportError(OSError):
    """Report a loopback HTTP failure with a credential-safe message."""


def _parse_loopback_url(url: str) -> tuple[SplitResult, int]:
    if not url.isascii() or _INVALID_URL_CHAR.search(url):
        raise LoopbackTransportError("Invalid loopback HTTP URL") from None

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise LoopbackTransportError("Invalid loopback HTTP URL") from None

    if (
        parsed.scheme != "http"
        or not _LOOPBACK_AUTHORITY.fullmatch(parsed.netloc)
        or port is None
        or port == 0
        or parsed.path.startswith("//")
    ):
        raise LoopbackTransportError("Invalid loopback HTTP URL") from None
    return parsed, port


def loopback_endpoint_url(endpoint: str, path: str) -> str:
    """Build a URL from a loopback origin and an absolute local route."""
    parsed, port = _parse_loopback_url(endpoint)
    if parsed.path not in {"", "/"} or "?" in endpoint:
        raise LoopbackTransportError("Invalid loopback HTTP endpoint") from None
    if (
        not path.startswith("/")
        or path.startswith("//")
        or not path.isascii()
        or _INVALID_URL_CHAR.search(path)
    ):
        raise LoopbackTransportError("Invalid loopback HTTP route") from None
    return f"http://{_LOOPBACK_HOST}:{port}{path}"


class LoopbackHttpClient:
    """Send single HTTP requests directly to the validated loopback address."""

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
        max_response_bytes: int | None = None,
    ) -> tuple[int, bytes]:
        """Return the status and complete body of a non-redirect response."""
        parsed, port = _parse_loopback_url(url)
        if max_response_bytes is not None and max_response_bytes < 0:
            raise LoopbackTransportError(
                "Invalid loopback HTTP response limit"
            ) from None

        target = parsed.path or "/"
        if "?" in url:
            target += f"?{parsed.query}"

        try:
            with closing(
                HTTPConnection(_LOOPBACK_HOST, port, timeout=timeout)
            ) as connection:
                connection.request(method, target, body=body, headers=headers)
                with closing(connection.getresponse()) as response:
                    if 300 <= response.status < 400:
                        raise LoopbackTransportError(
                            "Loopback HTTP redirect refused"
                        ) from None
                    if max_response_bytes is None:
                        return response.status, response.read()

                    data = response.read(max_response_bytes + 1)
                    if len(data) > max_response_bytes:
                        raise LoopbackTransportError(
                            "Loopback HTTP response exceeds byte limit"
                        ) from None
                    # A sized read can stop at EOF with part of Content-Length unread.
                    if response.length:
                        raise LoopbackTransportError(
                            "Loopback HTTP response incomplete"
                        ) from None
                    return response.status, data
        except LoopbackTransportError:
            raise
        except (HTTPException, OSError, ValueError, OverflowError):
            raise LoopbackTransportError("Loopback HTTP request failed") from None
