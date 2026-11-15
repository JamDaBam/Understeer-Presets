"""Tests of the comparison of a contribution with the published catalog.
Like test_catalog.py they need an Understeer checkout, no device and no
network."""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import compare_catalogs as cc  # noqa: E402
import validate_catalog as vc  # noqa: E402

try:
    LIBRARY = vc.load_library(vc.understeer_path())
except vc.SetupError as e:
    pytest.exit(str(e), returncode=2)


def entry(entry_id, name="Test", ff=70):
    return {"id": entry_id,
            "meta": {"author": "Tester", "game": "Test Game", "wheelbase": "CSL DD"},
            "preset": {"understeer_preset": 1, "name": name,
                       "values": {"FF": ff, "SEN": 900}}}


def raw(*entries):
    return json.dumps({"understeer_library": 1, "presets": list(entries)}).encode()


def compare(base, new):
    return cc.compare(raw(*base), raw(*new), LIBRARY)


def test_new_preset_is_routine():
    notes, warnings = compare([entry("a")], [entry("a"), entry("b", "B")])
    assert notes == ["New preset: b"] and warnings == []


def test_changed_preset_is_routine():
    notes, warnings = compare([entry("a")], [entry("a", ff=80)])
    assert notes == ["Changed preset: a"] and warnings == []


def test_unchanged():
    assert compare([entry("a")], [entry("a")]) == (["No preset changed."], [])


def test_removed_preset_needs_review():
    notes, warnings = compare([entry("a"), entry("b", "B")], [entry("a")])
    assert warnings == ["Preset b is removed. A maintainer has to check this."]


@pytest.mark.parametrize("new", [entry("b"), entry("b", ff=80)])
def test_changed_id_needs_review(new):
    """The same values, or the same name, under another id."""
    _notes, warnings = compare([entry("a")], [new])
    assert warnings == ["Preset id a is gone and b looks like the same "
                        "preset: ids must stay as they are. A maintainer has "
                        "to check this."]


def test_unreadable_contribution_compares_as_empty():
    _notes, warnings = cc.compare(raw(entry("a")), b"{not json", LIBRARY)
    assert warnings == ["Preset a is removed. A maintainer has to check this."]


def test_github_output(tmp_path, capsys, monkeypatch):
    base, new = tmp_path / "base.json", tmp_path / "new.json"
    base.write_bytes(raw(entry("a"), entry("b", "B")))
    new.write_bytes(raw(entry("a"), entry("c", "C", ff=90)))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert cc.main([str(base), str(new), "--github"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "New preset: c" in out
    warnings = [line for line in out if line.startswith("::warning")]
    assert warnings == ["::warning title=Maintainer review::Preset b is "
                        "removed. A maintainer has to check this."]
    text = summary.read_text()
    assert "New preset: c" in text and "1 point(s)" in text


def test_missing_file_is_a_setup_error(tmp_path):
    assert cc.main([str(tmp_path / "x"), str(tmp_path / "y")]) == 2
