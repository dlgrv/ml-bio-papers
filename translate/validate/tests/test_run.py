import pytest

from translate import run


def test_plan_includes_assets_and_verify_final():
    assert run.plan("fetch", have_source=False) == list(run.STEPS)
    assert run.plan("fetch", have_source=True) == [
        "digest",
        "assets",
        "translate",
        "render",
        "verify",
        "repair",
        "verify_final",
        "publish",
        "site",
    ]
    assert "assets" in run.STEPS
    assert "verify_final" in run.STEPS
    assert run.STEPS.count("verify") == 1


def test_from_verify_final():
    assert run.plan("verify_final", have_source=True) == [
        "verify_final",
        "publish",
        "site",
    ]


def test_unknown_step_rejected():
    with pytest.raises(ValueError, match="unknown step"):
        run.plan("nope", have_source=True)


def _patch_pipeline(monkeypatch, tmp_path, *, verify_main, repair_code=0):
    called: list[str] = []

    def track(name, code=0):
        def _fn(_argv=None):
            called.append(name)
            return code

        return _fn

    def work(slug, _root=None):
        return tmp_path / "runs" / slug

    (tmp_path / "runs" / "2019-x").mkdir(parents=True)
    monkeypatch.setattr(run, "work_dir", work)
    monkeypatch.setattr(run.verify_paper, "main", verify_main(called))
    monkeypatch.setattr(run.repair_units, "main", track("repair", repair_code))
    monkeypatch.setattr(run.build_paper, "main", track("publish", 0))
    monkeypatch.setattr(run.build_site, "main", track("site", 0))
    monkeypatch.setattr(run, "_write_state", lambda *_a, **_k: None)
    return called


def test_repair_skipped_on_clean_verify(monkeypatch, tmp_path):
    def verify_main(called):
        def _fn(_argv=None):
            called.append("verify")
            return 0

        return _fn

    called = _patch_pipeline(monkeypatch, tmp_path, verify_main=verify_main)
    code = run.main(["2019-x", "--from", "verify"])
    assert code == 0
    assert called == ["verify", "verify", "publish", "site"]
    assert "repair" not in called


def test_repair_runs_on_fail(monkeypatch, tmp_path):
    codes = iter([1, 0])

    def verify_main(called):
        def _fn(_argv=None):
            called.append("verify")
            return next(codes)

        return _fn

    called = _patch_pipeline(monkeypatch, tmp_path, verify_main=verify_main)
    code = run.main(["2019-x", "--from", "verify"])
    assert code == 0
    assert called == ["verify", "repair", "verify", "publish", "site"]
