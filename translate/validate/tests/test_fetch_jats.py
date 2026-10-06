from pathlib import Path
from unittest import mock

import pytest

from translate.steps.fetch import fetch_jats as fj

FIXTURE = (Path(__file__).parent / "fixtures" / "mini_article.xml").read_bytes()


def test_url_uses_efetch_with_numeric_id():
    url = fj.efetch_url("PMC6883579")
    assert url.startswith("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?")
    assert "db=pmc" in url
    assert "id=6883579" in url
    assert "retmode=xml" in url


@pytest.mark.parametrize("bad", ["6883579", "PMC", "PMCabc", ""])
def test_bad_pmcid_rejected(bad):
    with pytest.raises(ValueError, match="PMCID"):
        fj.efetch_url(bad)


def test_validate_accepts_article():
    fj.validate(FIXTURE)


@pytest.mark.parametrize(
    "body",
    [b"", b"<html>rate limited</html>", b"<pmc-articleset><error>bad id</error></pmc-articleset>"],
)
def test_validate_rejects_non_article(body):
    with pytest.raises(ValueError, match="article"):
        fj.validate(body)


def test_fetch_writes_source_xml_atomically(tmp_path):
    meta = tmp_path / "papers" / "2019-kraken2"
    meta.mkdir(parents=True)
    (meta / "meta.yml").write_text("pmcid: PMC6883579\n", encoding="utf-8")
    with mock.patch.object(fj, "download", return_value=FIXTURE) as dl:
        out = fj.fetch("2019-kraken2", root=str(tmp_path))
    dl.assert_called_once()
    assert out == tmp_path / "translate" / "runs" / "2019-kraken2" / "source.xml"
    assert out.read_bytes() == FIXTURE
    assert not list(out.parent.glob("*.tmp"))


def test_invalid_download_leaves_no_file(tmp_path):
    meta = tmp_path / "papers" / "2019-kraken2"
    meta.mkdir(parents=True)
    (meta / "meta.yml").write_text("pmcid: PMC6883579\n", encoding="utf-8")
    with (
        mock.patch.object(fj, "download", return_value=b"<html/>"),
        pytest.raises(ValueError, match="article"),
    ):
        fj.fetch("2019-kraken2", root=str(tmp_path))
    assert not (tmp_path / "translate" / "runs" / "2019-kraken2" / "source.xml").exists()


def test_missing_pmcid_in_meta(tmp_path):
    meta = tmp_path / "papers" / "2019-kraken2"
    meta.mkdir(parents=True)
    (meta / "meta.yml").write_text("title: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pmcid or arxiv"):
        fj.fetch("2019-kraken2", root=str(tmp_path))


ARXIV_HTML = (Path(__file__).parent / "fixtures" / "mini_latexml.html").read_bytes()


def test_arxiv_html_url():
    assert fj.arxiv_html_url("1810.04805") == "https://export.arxiv.org/html/1810.04805"
    assert fj.arxiv_html_url("1810.04805v2").endswith("1810.04805v2")


def test_bad_arxiv_id_rejected():
    with pytest.raises(ValueError, match="arxiv"):
        fj.arxiv_html_url("not-an-id")


def test_fetch_arxiv_converts_html_to_jats(tmp_path):
    meta = tmp_path / "papers" / "2019-bert"
    meta.mkdir(parents=True)
    (meta / "meta.yml").write_text("arxiv: 1810.04805\n", encoding="utf-8")
    with mock.patch.object(fj, "download", return_value=ARXIV_HTML) as dl:
        out = fj.fetch("2019-bert", root=str(tmp_path))
    dl.assert_called_once()
    xml = out.read_text(encoding="utf-8")
    assert "<article" in xml
    assert "Mini Transformer Paper" in xml
    assert "chrome" not in xml
