from translate.lib import pmc_media


def test_normalize_pmcid():
    assert pmc_media.normalize_pmcid("PMC6883579") == "PMC6883579"


def test_normalize_pmcid_rejects_digits_only():
    import pytest

    with pytest.raises(ValueError, match="PMCID"):
        pmc_media.normalize_pmcid("6883579")
