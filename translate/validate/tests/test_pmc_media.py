from translate.lib import pmc_media

HTML = "https://cdn.ncbi.nlm.nih.gov/pmc/blobs/aa/6883579/xx/13059_2019_1891_Fig1_HTML.jpg"
ORIG = "https://cdn.ncbi.nlm.nih.gov/pmc/blobs/aa/6883579/yy/13059_2019_1891_Fig1.jpg"
ARTICLE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6883579/"
JPEG_SMALL = b"\xff\xd8\xff" + b"s" * 40
JPEG_LARGE = b"\xff\xd8\xff" + b"L" * 400


def test_normalize_pmcid():
    assert pmc_media.normalize_pmcid("PMC6883579") == "PMC6883579"


def test_normalize_pmcid_rejects_digits_only():
    import pytest

    with pytest.raises(ValueError, match="PMCID"):
        pmc_media.normalize_pmcid("6883579")


def test_candidate_urls_prefer_stem_without_html_suffix():
    html = (
        f'<img src="{HTML}"/>'
        f'<a href="{ORIG}">original</a>'
        '<a href="https://cdn.ncbi.nlm.nih.gov/pmc/blobs/aa/6883579/zz/other_Fig2.jpg">no</a>'
    )
    got = pmc_media.candidate_graphic_urls("PMC6883579", "13059_2019_1891_Fig1_HTML.jpg", html)
    assert got == [HTML, ORIG]


def test_pick_largest_image_skips_non_images_and_failed_urls():
    def dl(url: str) -> bytes:
        if url == HTML:
            return JPEG_SMALL
        if url == ORIG:
            return JPEG_LARGE
        raise OSError("nope")

    url, data = pmc_media.pick_largest_image([HTML, ORIG, "https://example.com/x.jpg"], dl)
    assert url == ORIG
    assert data == JPEG_LARGE


def test_pick_largest_image_keeps_html_when_original_missing():
    def dl(url: str) -> bytes:
        if url == HTML:
            return JPEG_SMALL
        raise OSError("404")

    url, data = pmc_media.pick_largest_image([HTML, ORIG], dl)
    assert url == HTML
    assert data == JPEG_SMALL
