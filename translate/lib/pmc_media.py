"""Resolve PMC figure binaries to downloadable CDN URLs.

The JATS ``xlink:href`` is a basename only. The old ``…/articles/PMC…/bin/``
path often returns an HTML error page; the HTML article page links the real
files under ``cdn.ncbi.nlm.nih.gov/pmc/blobs/…``. When PMC also publishes a
larger original next to the ``*_HTML.jpg`` preview, pick the largest raster.
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
STEM_HTML_RE = re.compile(r"_HTML(?=\.(?:jpe?g|png|gif)\b)", re.IGNORECASE)
RASTER_EXT = {".jpg", ".jpeg", ".png", ".gif"}

IMAGE_MAGIC = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
)


def is_image_bytes(data: bytes) -> bool:
    if any(data.startswith(magic) for magic, _ in IMAGE_MAGIC):
        return True
    head = data.lstrip()[:800].lower()
    if b"<html" in head:
        return False
    return b"<svg" in head


def normalize_pmcid(pmcid: str) -> str:
    if not PMCID_RE.fullmatch(pmcid):
        raise ValueError(f"bad PMCID {pmcid!r}: expected PMC<digits>")
    return pmcid


def _stem(name: str) -> str:
    base = name.rsplit("/", 1)[-1].split("?", 1)[0]
    stem = STEM_HTML_RE.sub("", base)
    lower = stem.lower()
    for ext in (".jpeg", ".jpg", ".png", ".gif"):
        if lower.endswith(ext):
            return stem[: -len(ext)]
    return stem


def _href_name(href: str) -> str:
    return href.rsplit("/", 1)[-1].split("?", 1)[0]


def candidate_graphic_urls(pmcid: str, filename: str, html: str) -> list[str]:
    """HTTPS image URLs on the article page that belong to ``filename``."""
    pmcid = normalize_pmcid(pmcid)
    base = PMC_ARTICLE.format(pmcid=pmcid)
    stem = _stem(filename).lower()
    exact = filename.rsplit("/", 1)[-1].split("?", 1)[0]
    found: list[str] = []
    seen: set[str] = set()
    for href in HREF_RE.findall(html):
        name = _href_name(href)
        lower = name.lower()
        ext_i = lower.rfind(".")
        ext = lower[ext_i:] if ext_i >= 0 else ""
        if ext not in RASTER_EXT:
            continue
        if name != exact and _stem(name).lower() != stem:
            continue
        abs_url = urljoin(base, href)
        if not abs_url.startswith("https://") or abs_url in seen:
            continue
        seen.add(abs_url)
        found.append(abs_url)
    return found


def pick_largest_image(
    urls: list[str],
    download: Callable[[str], bytes],
) -> tuple[str, bytes] | None:
    best: tuple[str, bytes] | None = None
    for url in urls:
        try:
            data = download(url)
        except (OSError, ValueError):
            continue
        if not is_image_bytes(data):
            continue
        if best is None or len(data) > len(best[1]):
            best = (url, data)
    return best


def resolve_best_graphics(
    pmcid: str,
    filenames: list[str],
    *,
    download: Callable[[str], bytes] | None = None,
) -> dict[str, tuple[str, bytes]]:
    """Map JATS basenames to (url, image bytes) of the largest matching raster."""
    pmcid = normalize_pmcid(pmcid)
    wanted = list(dict.fromkeys(filenames))
    if not wanted:
        return {}
    dl = default_download if download is None else download
    html = dl(PMC_ARTICLE.format(pmcid=pmcid)).decode("utf-8", errors="replace")
    found: dict[str, tuple[str, bytes]] = {}
    for name in wanted:
        urls = candidate_graphic_urls(pmcid, name, html)
        picked = pick_largest_image(urls, dl) if urls else None
        if picked:
            found[name] = picked
    return found


def resolve_graphic_urls(
    pmcid: str,
    filenames: list[str],
    *,
    download: Callable[[str], bytes] | None = None,
) -> dict[str, str]:
    """Map graphic basenames to the largest matching HTTPS URL on the PMC page."""
    return {
        name: url
        for name, (url, _data) in resolve_best_graphics(pmcid, filenames, download=download).items()
    }
