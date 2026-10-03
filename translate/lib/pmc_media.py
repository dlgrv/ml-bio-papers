"""Resolve PMC figure binaries to downloadable CDN URLs.

The JATS ``xlink:href`` is a basename only. The old ``…/articles/PMC…/bin/``
path often returns an HTML error page; the HTML article page links the real
files under ``cdn.ncbi.nlm.nih.gov/pmc/blobs/…``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from translate.lib.http import download as default_download

if TYPE_CHECKING:
    from collections.abc import Callable

PMCID_RE = re.compile(r"PMC\d+")
PMC_ARTICLE = "https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
HREF_RE = re.compile(r"""(?:src|href)=["']([^"']+)["']""", re.IGNORECASE)

IMAGE_MAGIC = (
    (b"\xff\xd8\xff", ".jpg"),  # JPEG
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
)


def is_image_bytes(data: bytes) -> bool:
    return any(data.startswith(magic) for magic, _ in IMAGE_MAGIC)


def normalize_pmcid(pmcid: str) -> str:
    if not PMCID_RE.fullmatch(pmcid):
        raise ValueError(f"bad PMCID {pmcid!r}: expected PMC<digits>")
    return pmcid


def resolve_graphic_urls(
    pmcid: str,
    filenames: list[str],
    *,
    download: Callable[[str], bytes] | None = None,
) -> dict[str, str]:
    """Map graphic basenames to absolute HTTPS URLs found on the PMC article page."""
    pmcid = normalize_pmcid(pmcid)
    wanted = set(filenames)
    if not wanted:
        return {}
    dl = default_download if download is None else download
    html = dl(PMC_ARTICLE.format(pmcid=pmcid)).decode("utf-8", errors="replace")
    base = PMC_ARTICLE.format(pmcid=pmcid)
    found: dict[str, str] = {}
    for href in HREF_RE.findall(html):
        name = href.rsplit("/", 1)[-1].split("?", 1)[0]
        if name not in wanted or name in found:
            continue
        abs_url = urljoin(base, href)
        if abs_url.startswith("https://"):
            found[name] = abs_url
    return found
