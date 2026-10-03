#!/usr/bin/env python3
"""Download figure binaries from PMC into papers/<slug>/assets/.

Reads `pmcid` from papers/<slug>/meta.yml and graphic filenames from figure units in
translate/runs/<slug>/units.json. Resolves real CDN URLs from the PMC article HTML
(``translate.lib.pmc_media``). Skips files that already exist and look like images.
Usage: python -m translate.steps.fetch.fetch_assets <slug>
"""

from __future__ import annotations

import os
import sys
import urllib.error
from typing import TYPE_CHECKING

import yaml

from translate.lib.http import download as default_download
from translate.lib.jsonio import read_json
from translate.lib.paths import assets_dir, meta_yml, work_dir
from translate.lib.pmc_media import is_image_bytes, resolve_graphic_urls

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_DOWNLOAD_ERRORS = (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError)


def collect_graphics(units: list) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for unit in units:
        if unit.get("kind") != "figure":
            continue
        for name in unit.get("graphics") or []:
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def _needs_download(dest: Path) -> bool:
    if not dest.exists() or dest.stat().st_size == 0:
        return True
    return not is_image_bytes(dest.read_bytes()[:16])


def fetch_assets(
    slug: str,
    root: str | None = None,
    *,
    download: Callable[[str], bytes] | None = None,
) -> int:
    dl = default_download if download is None else download
    meta = yaml.safe_load(meta_yml(slug, root).read_text(encoding="utf-8")) or {}
    pmcid = meta.get("pmcid")
    if not pmcid:
        print(f"{meta_yml(slug, root)}: no pmcid", file=sys.stderr)
        return 2
    units = read_json(work_dir(slug, root) / "units.json", [])
    graphics = collect_graphics(units)
    if not graphics:
        return 0
    out_dir = assets_dir(slug, root)
    out_dir.mkdir(parents=True, exist_ok=True)
    pending = [name for name in graphics if _needs_download(out_dir / name)]
    if not pending:
        return 0
    try:
        urls = resolve_graphic_urls(str(pmcid), pending, download=dl)
    except _DOWNLOAD_ERRORS as e:
        print(f"{slug}: resolve PMC media failed: {e}", file=sys.stderr)
        return 1
    for filename in pending:
        url = urls.get(filename)
        if not url:
            print(f"{slug}: no CDN URL for {filename}", file=sys.stderr)
            return 1
        try:
            data = dl(url)
        except _DOWNLOAD_ERRORS as e:
            print(f"{slug}: download failed {filename}: {e}", file=sys.stderr)
            return 1
        if not is_image_bytes(data):
            print(f"{slug}: not an image: {filename} from {url}", file=sys.stderr)
            return 1
        dest = out_dir / filename
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        print(f"{slug}: {dest.stat().st_size} bytes -> {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    return fetch_assets(args[0])


if __name__ == "__main__":
    raise SystemExit(main())
