import json
from pathlib import Path
from unittest import mock

from translate.lib import pmc_media
from translate.steps.fetch import fetch_assets as fa

FIGURE_UNITS = [
    {"kind": "para", "id": "p1", "text": "body"},
    {
        "kind": "figure",
        "id": "f1",
        "graphics": ["13059_2019_1891_Fig1_HTML.jpg"],
    },
]

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
CDN = (
    "https://cdn.ncbi.nlm.nih.gov/pmc/blobs/1a33/6883579/72ab03bb5d39/13059_2019_1891_Fig1_HTML.jpg"
)
ARTICLE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6883579/"


def _layout(
    tmp_path: Path, slug: str = "2019-kraken2", *, pmcid: str | None = "PMC6883579", units=None
):
    paper = tmp_path / "papers" / slug
    paper.mkdir(parents=True)
    if pmcid is None:
        (paper / "meta.yml").write_text("title: x\n", encoding="utf-8")
    else:
        (paper / "meta.yml").write_text(f"pmcid: {pmcid}\n", encoding="utf-8")
    wd = tmp_path / "translate" / "runs" / slug
    wd.mkdir(parents=True)
    (wd / "units.json").write_text(
        json.dumps(units if units is not None else FIGURE_UNITS), encoding="utf-8"
    )
    return paper / "assets"


def _dl_for_article_and_image(html: bytes | None = None):
    html = html or f'<img src="{CDN}"/>'.encode()

    def dl(url: str) -> bytes:
        if url.rstrip("/") == ARTICLE.rstrip("/") or url == ARTICLE:
            return html
        if url == CDN:
            return JPEG
        raise OSError(f"unexpected url {url}")

    return dl


def test_is_image_bytes_jpeg_and_rejects_html():
    assert pmc_media.is_image_bytes(JPEG)
    assert not pmc_media.is_image_bytes(b"<!doctype html>")


def test_resolve_graphic_urls_from_article_html():
    html = f'<html><img src="{CDN}"/></html>'.encode()

    def dl(url: str) -> bytes:
        if url.rstrip("/") == ARTICLE.rstrip("/"):
            return html
        if url == CDN:
            return JPEG
        raise OSError(url)

    got = pmc_media.resolve_graphic_urls(
        "PMC6883579", ["13059_2019_1891_Fig1_HTML.jpg"], download=dl
    )
    assert got == {"13059_2019_1891_Fig1_HTML.jpg": CDN}


def test_fetch_assets_writes_largest_candidate(tmp_path):
    orig = CDN.replace("_HTML.jpg", ".jpg")
    large = b"\xff\xd8\xff" + b"L" * 400
    html = f'<img src="{CDN}"/><a href="{orig}">hi</a>'.encode()

    def dl(url: str) -> bytes:
        if url.rstrip("/") == ARTICLE.rstrip("/"):
            return html
        if url == CDN:
            return JPEG
        if url == orig:
            return large
        raise OSError(url)

    assets = _layout(tmp_path)
    assert fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=dl) == 0
    dest = assets / "13059_2019_1891_Fig1_HTML.jpg"
    assert dest.read_bytes() == large


def test_fetch_assets_downloads_graphics(tmp_path):
    assets = _layout(tmp_path)
    assert (
        fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=_dl_for_article_and_image())
        == 0
    )
    dest = assets / "13059_2019_1891_Fig1_HTML.jpg"
    assert dest.read_bytes() == JPEG
    assert not list(assets.glob("*.tmp"))


def test_fetch_assets_skips_existing_image(tmp_path):
    assets = _layout(tmp_path)
    dest = assets / "13059_2019_1891_Fig1_HTML.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(JPEG)
    n_image = {"n": 0}

    def dl(url: str) -> bytes:
        if url.rstrip("/") == ARTICLE.rstrip("/"):
            return f'<img src="{CDN}"/>'.encode()
        if url == CDN:
            n_image["n"] += 1
            return JPEG
        raise OSError(url)

    assert fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=dl) == 0
    assert dest.read_bytes() == JPEG
    assert n_image["n"] == 1


def test_fetch_assets_redownloads_html_placeholder(tmp_path):
    assets = _layout(tmp_path)
    dest = assets / "13059_2019_1891_Fig1_HTML.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"<!doctype html>fake")
    assert (
        fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=_dl_for_article_and_image())
        == 0
    )
    assert dest.read_bytes() == JPEG


def test_fetch_assets_exit_1_on_download_error(tmp_path):
    _layout(tmp_path)
    dl = mock.Mock(side_effect=OSError("HTTP fail"))
    assert fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=dl) == 1


def test_fetch_assets_empty_graphics(tmp_path):
    _layout(tmp_path, units=[{"kind": "para", "id": "p1", "text": "only text"}])
    dl = mock.Mock(return_value=b"img")
    assert fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=dl) == 0
    dl.assert_not_called()


def test_fetch_assets_missing_pmcid(tmp_path):
    _layout(tmp_path, pmcid=None)
    dl = mock.Mock(return_value=b"img")
    assert fa.fetch_assets("2019-kraken2", root=str(tmp_path), download=dl) == 2
    dl.assert_not_called()
