"""Shared HTTPS fetch helpers (NCBI rate limit + User-Agent)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

MIN_INTERVAL_S = 0.34  # NCBI: ≤3 req/s without an API key
USER_AGENT = "ml-bio-papers/0.1 (translation pipeline)"
_last_request = 0.0


def download(url: str, timeout: float = 60.0) -> bytes:
    """GET an https URL with shared throttle. Raises urllib.error.URLError / HTTPError."""
    global _last_request  # noqa: PLW0603 - module-level throttle shared by all callers
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    if not url.startswith("https://"):
        raise ValueError(f"refusing non-https URL {url!r}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


def http_error_code(exc: BaseException) -> int | None:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code
    return None
