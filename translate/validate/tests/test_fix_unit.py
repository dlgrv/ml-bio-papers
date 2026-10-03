import json

import pytest

from translate.lib import mask
from translate.steps.fix import fix_unit

UNIT = {"id": "u001", "text": "We used ⟦V1⟧ reads.", "spans": {}}


def _wd(tmp_path, status="needs_repair"):
    wd = tmp_path / "translate" / "runs" / "2019-x"
    wd.mkdir(parents=True)
    (wd / "units.json").write_text(json.dumps([UNIT]))
    (wd / "translated.json").write_text(
        json.dumps({"u001": {"status": status, "text": "bad", "error": "x"}})
    )
    return wd


def test_valid_text_is_stored_as_ok_manual(tmp_path):
    wd = _wd(tmp_path)
    fix_unit.fix("2019-x", "u001", "Мы использовали ⟦V1⟧ ридов.", root=str(tmp_path))
    res = json.loads((wd / "translated.json").read_text())
    assert res["u001"] == {"status": "ok", "text": "Мы использовали ⟦V1⟧ ридов.", "manual": True}


def test_lost_placeholder_is_rejected_and_nothing_written(tmp_path):
    wd = _wd(tmp_path)
    before = (wd / "translated.json").read_text()
    with pytest.raises(mask.PlaceholderError):
        fix_unit.fix("2019-x", "u001", "Мы использовали риды.", root=str(tmp_path))
    assert (wd / "translated.json").read_text() == before


def test_unknown_unit_is_rejected(tmp_path):
    _wd(tmp_path)
    with pytest.raises(KeyError):
        fix_unit.fix("2019-x", "u999", "текст", root=str(tmp_path))
