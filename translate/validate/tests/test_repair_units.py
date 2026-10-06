import json

from translate.steps.repair import repair_units as ru

SLUG = "2019-x"


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages, **_kw):
        self.calls.append(messages)
        if not self.replies:
            raise AssertionError("unexpected extra LLM call")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def _layout(tmp_path, units, results):
    root = tmp_path
    (root / "glossary").mkdir()
    (root / "glossary" / "README.md").write_text(
        "| Термин | Перевод | Примечание |\n|---|---|---|\n"
        "| lowest common ancestor (LCA) | наименьший общий предок | |\n"
        "| k-mer | k-мер | |\n",
        encoding="utf-8",
    )
    rules = root / "translate" / "rules"
    rules.mkdir(parents=True)
    (rules / "ru.json").write_text('{"banned_calques": []}\n', encoding="utf-8")
    prompt = root / "translate" / "prompts"
    prompt.mkdir(parents=True)
    (prompt / "repair-unit.md").write_text("Repair the translation.\n", encoding="utf-8")
    wd = root / "translate" / "runs" / SLUG
    wd.mkdir(parents=True)
    (wd / "units.json").write_text(json.dumps(units), encoding="utf-8")
    (wd / "translated.json").write_text(json.dumps(results), encoding="utf-8")
    (wd / "body.en.md").write_text("en\n", encoding="utf-8")
    (wd / "body.ru.md").write_text("ru\n", encoding="utf-8")
    return root, wd


def _para(uid, text):
    return {
        "id": uid,
        "kind": "para",
        "translate": True,
        "text": text,
        "spans": {},
        "source_md": text,
        "src_id": None,
        "level": 0,
        "label": "",
        "graphics": [],
    }


def test_mechanical_restores_doi(tmp_path):
    src = "See doi:10.1093/bioinformatics/bty648 for details."
    bad = "См. doi:10.1099/bioinformatics/bty648 для деталей."
    units = [_para("u001", src)]
    results = {"u001": {"status": "ok", "text": bad}}
    root, wd = _layout(tmp_path, units, results)
    llm = FakeLLM([])
    code = ru.repair_units(SLUG, root=str(root), llm=llm)
    assert llm.calls == []
    out = json.loads((wd / "translated.json").read_text(encoding="utf-8"))
    assert out["u001"]["status"] == "ok"
    assert "10.1093" in out["u001"]["text"]
    assert "10.1099" not in out["u001"]["text"]
    assert out["u001"].get("repaired") == "mechanical"
    assert code == 0


def test_llm_repair_stub(tmp_path):
    src = "We used the lowest common ancestor."
    bad = "Мы использовали общий родитель."
    good = "Мы использовали наименьший общий предок."
    units = [_para("u001", src)]
    results = {"u001": {"status": "ok", "text": bad}}
    root, wd = _layout(tmp_path, units, results)
    llm = FakeLLM([good])
    code = ru.repair_units(SLUG, root=str(root), llm=llm)
    assert len(llm.calls) == 1
    out = json.loads((wd / "translated.json").read_text(encoding="utf-8"))
    assert out["u001"]["status"] == "ok"
    assert out["u001"]["text"] == good
    assert out["u001"].get("repaired") == "llm"
    assert code == 0
    report = json.loads((wd / "repair_report.json").read_text(encoding="utf-8"))
    assert report["leftover"] == []


def test_max_rounds_leaves_needs_repair(tmp_path):
    src = "We used the lowest common ancestor."
    bad = "Мы использовали общий родитель."
    still_bad = "Мы использовали родителя."
    units = [_para("u001", src)]
    results = {"u001": {"status": "ok", "text": bad}}
    root, wd = _layout(tmp_path, units, results)
    llm = FakeLLM([still_bad, still_bad])
    code = ru.repair_units(SLUG, root=str(root), llm=llm)
    assert len(llm.calls) == 2
    out = json.loads((wd / "translated.json").read_text(encoding="utf-8"))
    assert out["u001"]["status"] == "needs_repair"
    report = json.loads((wd / "repair_report.json").read_text(encoding="utf-8"))
    assert "u001" in report["leftover"]
    assert code == 1


def test_paper_level_links_skip_units_with_matching_urls(tmp_path):
    ok_src = "See [https://example.com/a](https://example.com/a)."
    ok_ru = "См. [https://example.com/a](https://example.com/a)."
    bad_src = (
        "Board [https://gluebenchmark.com/leaderboard](https://gluebenchmark.com/leaderboard)."
    )
    bad_ru = (
        "Доска [https://gluebenchmark.com/leaderboard,](https://gluebenchmark.com/leaderboard,)."
    )
    units = [_para("u001", ok_src), _para("u002", bad_src)]
    results = {
        "u001": {"status": "ok", "text": ok_ru},
        "u002": {"status": "ok", "text": bad_ru},
    }
    root, wd = _layout(tmp_path, units, results)
    llm = FakeLLM([])
    code = ru.repair_units(SLUG, root=str(root), llm=llm)
    assert llm.calls == []
    out = json.loads((wd / "translated.json").read_text(encoding="utf-8"))
    assert out["u001"]["text"] == ok_ru
    assert out["u001"]["status"] == "ok"
    assert "leaderboard," not in out["u002"]["text"]
    assert "leaderboard" in out["u002"]["text"]
    assert code == 0
