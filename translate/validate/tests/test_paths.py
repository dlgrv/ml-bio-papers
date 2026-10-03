from pathlib import Path

import pytest

from translate.lib import config, paths


def test_paper_paths_under_root(tmp_path):
    root = str(tmp_path)
    assert paths.paper_dir("2019-kraken2", root) == tmp_path / "papers" / "2019-kraken2"
    assert paths.index_md("2019-kraken2", root) == tmp_path / "papers" / "2019-kraken2" / "index.md"
    assert paths.meta_yml("2019-kraken2", root).name == "meta.yml"
    assert paths.work_dir("2019-kraken2", root) == tmp_path / "translate" / "runs" / "2019-kraken2"
    assert paths.source_xml("2019-kraken2", root).name == "source.xml"


def test_assets_dir(tmp_path):
    root = str(tmp_path)
    assert paths.assets_dir("2019-kraken2", root) == tmp_path / "papers" / "2019-kraken2" / "assets"


@pytest.mark.parametrize("slug", ["../etc", "kraken2", "2019/kraken2", "2019-Kraken2", ""])
def test_bad_slug_rejected(slug):
    with pytest.raises(ValueError, match="slug"):
        paths.paper_dir(slug)


def test_default_root_is_repo_root():
    assert (Path(config.default_root()) / "TRANSLATION.md").is_file()


def test_load_rules_missing_pack_is_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        config.load_rules(str(tmp_path))
