import json

import pytest

from translate.lib import glossary as gl
from translate.llm.client import LLMError
from translate.steps.translate import translate_units as tu

TERMS = gl.parse(
    "| Термин | Перевод | Примечание |\n|---|---|---|\n"
    "| lowest common ancestor (LCA) | наименьший общий предок | |\n"
    "| k-mer | k-мер | |\n"
)

READ_TERMS = gl.parse(
    "| Термин | Перевод | Примечание |\n|---|---|---|\n"
    "| read | рид | короткий фрагмент ДНК после секвенирования |\n"
)


def unit(uid, text, *, translate=True, spans=None):
    return {
        "id": uid,
        "kind": "para",
        "translate": translate,
        "text": text,
        "spans": spans or {},
        "source_md": text,
    }


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def __call__(self, messages, **_kw):
        self.calls.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def run(units, llm, tmp_path, *, terms=TERMS, **kw):
    return tu.translate_units(units, llm, terms, tmp_path / "translated.json", **kw)


def test_happy_path_writes_result_and_skips_untranslatable(tmp_path):
    units = [unit("u001", "A ⟦V1⟧-mer."), unit("u002", "ref", translate=False)]
    llm = FakeLLM(["⟦V1⟧-мер."])
    res = run(units, llm, tmp_path)
    assert res["u001"]["status"] == "ok"
    assert res["u001"]["text"] == "⟦V1⟧-мер."
    assert "u002" not in res
    assert json.loads((tmp_path / "translated.json").read_text())["u001"]["text"] == "⟦V1⟧-мер."


def test_prompt_contains_glossary_subset_only(tmp_path):
    llm = FakeLLM(["x"])
    run([unit("u001", "the k-mer length")], llm, tmp_path)
    user = llm.calls[0][1]["content"]
    assert "k-mer → k-мер (k-mer)" in user
    assert "lowest common ancestor" not in user
    assert user.rstrip().endswith("the k-mer length")


def test_dropped_placeholder_retries_with_error_then_ok(tmp_path):
    llm = FakeLLM(["потеряно", "⟦V1⟧ ок"])
    res = run([unit("u001", "⟦V1⟧ ok")], llm, tmp_path)
    assert res["u001"]["status"] == "ok"
    assert len(llm.calls) == 2
    assert "missing placeholders: ⟦V1⟧" in llm.calls[1][-1]["content"]


def test_still_failing_after_retries_is_needs_repair_with_last_draft(tmp_path):
    llm = FakeLLM(["a", "b", "c"])
    res = run([unit("u001", "⟦V1⟧ ok")], llm, tmp_path, retries=2)
    assert res["u001"]["status"] == "needs_repair"
    assert res["u001"]["text"] == "c"
    assert "missing" in res["u001"]["error"]
    assert len(llm.calls) == 3


def test_llm_error_is_needs_repair_and_run_continues(tmp_path):
    llm = FakeLLM(
        [LLMError("empty content"), LLMError("empty content"), LLMError("empty content"), "второй"]
    )
    res = run([unit("u001", "one"), unit("u002", "two")], llm, tmp_path, retries=2)
    assert res["u001"]["status"] == "needs_repair"
    assert "empty content" in res["u001"]["error"]
    assert res["u002"]["status"] == "ok"


def test_resume_skips_finished_units(tmp_path):
    out = tmp_path / "translated.json"
    out.write_text(json.dumps({"u001": {"status": "ok", "text": "готово"}}))
    llm = FakeLLM(["второй"])
    res = run([unit("u001", "one"), unit("u002", "two")], llm, tmp_path)
    assert len(llm.calls) == 1
    assert res["u001"]["text"] == "готово"
    assert res["u002"]["text"] == "второй"


def test_resume_retries_needs_repair_units(tmp_path):
    (tmp_path / "translated.json").write_text(
        json.dumps({"u001": {"status": "needs_repair", "text": "bad"}})
    )
    llm = FakeLLM(["хорошо"])
    res = run([unit("u001", "one")], llm, tmp_path)
    assert res["u001"]["status"] == "ok"


def test_corrupt_result_file_is_an_error_not_silent_restart(tmp_path):
    (tmp_path / "translated.json").write_text('{"u001": ')
    with pytest.raises(ValueError, match="corrupt"):
        run([unit("u001", "one")], FakeLLM(["x"]), tmp_path)


def test_write_is_atomic_no_tmp_left(tmp_path):
    run([unit("u001", "one")], FakeLLM(["один"]), tmp_path)
    assert [p.name for p in tmp_path.iterdir()] == ["translated.json"]


def test_context_is_previous_source_sentences_read_only(tmp_path):
    llm = FakeLLM(["a", "b"])
    run([unit("u001", "First sentence. Second one."), unit("u002", "Third.")], llm, tmp_path)
    assert "Second one." in llm.calls[1][1]["content"]
    assert "Context (do not translate)" in llm.calls[1][1]["content"]


def test_abbreviation_state_first_use_then_short():
    units = [unit("u001", "a lowest common ancestor (LCA) here"), unit("u002", "the LCA again")]
    seen = tu.abbrev_state(units, TERMS, upto=1)
    assert seen == {"LCA"}
    assert tu.abbrev_state(units, TERMS, upto=0) == set()


def test_abbreviation_note_in_prompt(tmp_path):
    llm = FakeLLM(["a", "b"])
    units = [unit("u001", "a lowest common ancestor (LCA) here"), unit("u002", "the LCA again")]
    run(units, llm, tmp_path)
    first, second = llm.calls[0][1]["content"], llm.calls[1][1]["content"]
    assert "first use: LCA" in first
    assert "already introduced: LCA" in second


def test_first_mention_en_in_prompt(tmp_path):
    llm = FakeLLM(["a", "b"])
    units = [unit("u001", "Each read is kept."), unit("u002", "Another read follows.")]
    run(units, llm, tmp_path, terms=READ_TERMS)
    first, second = llm.calls[0][1]["content"], llm.calls[1][1]["content"]
    assert "read → рид (read; короткий фрагмент ДНК после секвенирования)" in first
    assert "first use: read" in first
    assert "already introduced: read" in second
    assert "read → рид (read;" not in second


def test_abbreviation_state_is_deterministic_on_resume(tmp_path):
    units = [unit("u001", "a lowest common ancestor (LCA) here"), unit("u002", "the LCA again")]
    (tmp_path / "translated.json").write_text(json.dumps({"u001": {"status": "ok", "text": "x"}}))
    llm = FakeLLM(["b"])
    run(units, llm, tmp_path)
    assert "already introduced: LCA" in llm.calls[0][1]["content"]


def test_prompt_glossary_sees_k_mer_behind_variable_placeholder(tmp_path):
    spans = {"⟦V1⟧": {"type": "V", "md": "*k*"}}
    llm = FakeLLM(["⟦V1⟧-мер"])
    run([unit("u001", "⟦V1⟧-mer", spans=spans)], llm, tmp_path)
    assert "k-mer → k-мер (k-mer)" in llm.calls[0][1]["content"]
