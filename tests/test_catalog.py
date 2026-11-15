"""Tests of the submission check. They need an Understeer checkout (see
scripts/validate_catalog.py), no device and no network."""
import copy
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import validate_catalog as vc  # noqa: E402

try:
    LIBRARY = vc.load_library(vc.understeer_path())
except vc.SetupError as e:
    pytest.exit(str(e), returncode=2)


def entry(entry_id="test-preset", **meta):
    data = {"id": entry_id,
            "meta": {"author": "Tester", "game": "Test Game",
                     "wheelbase": "CSL DD"},
            "preset": {"understeer_preset": 1, "name": "Test",
                       "values": {"FF": 70, "SEN": 900}}}
    for key, value in meta.items():
        if value is None:
            data["meta"].pop(key, None)
        else:
            data["meta"][key] = value
    return data


def catalog(*entries, version=1):
    return {"understeer_library": version, "presets": list(entries)}


def check(data):
    raw = data if isinstance(data, bytes) else json.dumps(data).encode()
    return vc.validate(raw, LIBRARY)


def errors(data):
    return check(data)[0]


def test_published_catalog_is_clean():
    errs, warnings = vc.validate((REPO / "catalog.json").read_bytes(), LIBRARY)
    assert (errs, warnings) == ([], [])


def test_published_examples_are_marked_as_demos():
    data = json.loads((REPO / "catalog.json").read_text(encoding="utf-8"))
    for item in data["presets"]:
        assert item["id"].startswith("example-")
        assert "Demo" in item["preset"]["name"]
        assert "demo" in item["meta"]["tags"]
        assert "Demonstration entry only" in item["meta"]["description"]


def test_valid_catalog():
    assert errors(catalog(entry())) == []


def test_multiple_valid_presets():
    assert errors(catalog(entry("a"), entry("b"), entry("c"))) == []


def test_empty_catalog():
    assert errors(catalog()) == ["Catalog: there is no preset in it."]


def test_duplicate_ids():
    errs = errors(catalog(entry("same"), entry("same")))
    assert errs == ["Preset 2 (same): the id is used already."]


@pytest.mark.parametrize("key", vc.REQUIRED_META)
@pytest.mark.parametrize("value", [None, "", "   "])
def test_required_metadata(key, value):
    errs = errors(catalog(entry(**{key: value})))
    assert errs == [f"Preset 1 (test-preset): meta.{key} is required and "
                    "must not be empty."]


def test_wrong_metadata_type():
    errs = errors(catalog(entry(author=["Tester"])))
    assert errs == ["Preset 1 (test-preset): meta.author is not text."]


@pytest.mark.parametrize("values, reason", [
    ({"FF": 101}, "preset.values.FF is out of range or no number"),
    ({"FF": "70"}, "preset.values.FF is out of range or no number"),
    ({"FF": 70.5}, "preset.values.FF is out of range or no number"),
    ({"FF": True}, "preset.values.FF is out of range or no number"),
    ({"FFS": 3}, "preset.values.FFS is out of range or no number"),
    ({}, "preset.values is not an object with settings"),
    ([70], "preset.values is not an object with settings"),
])
def test_invalid_tuning_value(values, reason):
    item = entry()
    item["preset"]["values"] = values
    assert errors(catalog(item)) == [f"Preset 1 (test-preset): {reason}."]


def test_unknown_tuning_setting():
    item = entry()
    item["preset"]["values"]["NEW"] = 1
    assert errors(catalog(item)) == [
        "Preset 1 (test-preset): settings Understeer doesn't know: NEW."]


def test_adjusted_value():
    item = entry()
    item["preset"]["values"].update(SEN=905, SHO=35)
    assert errors(catalog(item)) == [
        "Preset 1 (test-preset): SEN is 905, but Understeer would keep 900; use 900.",
        "Preset 1 (test-preset): SHO is 35, but Understeer would keep 30; use 30."]


@pytest.mark.parametrize("version, message", [
    (2, "the catalog needs a newer version of Understeer"),
    (0, "this is no Understeer preset catalog"),
    ("1", "this is no Understeer preset catalog"),
])
def test_invalid_catalog_version(version, message):
    assert errors(catalog(entry(), version=version)) == [f"Catalog: {message}."]


def test_unsupported_preset_format():
    item = entry()
    item["preset"]["understeer_preset"] = 2
    assert errors(catalog(item)) == [
        "Preset 1 (test-preset): preset.understeer_preset is missing or not supported."]


def test_duplicate_json_keys():
    raw = (b'{"understeer_library": 1, "presets": [{"id": "a", "id": "b", '
           b'"preset": {"understeer_preset": 1, "name": "A", "values": {"FF": 1}}}]}')
    assert errors(raw) == ["Catalog: duplicate key in a JSON object."]


@pytest.mark.parametrize("number", [b"NaN", b"Infinity", b"-Infinity"])
def test_invalid_numbers(number):
    raw = (b'{"understeer_library": 1, "presets": [{"id": "a", "preset": '
           b'{"understeer_preset": 1, "name": "A", "values": {"FF": '
           + number + b'}}}]}')
    assert errors(raw) == [f"Catalog: {number.decode()} is not a "
                           "number in JSON."]


def test_excessive_nesting():
    assert errors(b"[" * 100000 + b"]" * 100000) == [
        "Catalog: the catalog is nested too deeply."]


@pytest.mark.parametrize("raw", [b"", b"{", b'{"understeer_library": 1,}',
                                 b"\xff\xfe"])
def test_malformed_json(raw):
    errs = errors(raw)
    assert len(errs) == 1 and errs[0].startswith("Catalog: the catalog is ")


def test_oversized_catalog():
    raw = json.dumps(catalog(entry())).encode()
    raw = raw[:-1] + b" " * (LIBRARY.MAX_CATALOG_BYTES - len(raw) + 1) + b"}"
    assert errors(raw) == ["Catalog: the catalog is too big."]


def test_too_many_presets():
    many = catalog(*(entry(f"p{i}") for i in range(LIBRARY.MAX_ENTRIES + 1)))
    assert errors(many) == ["Catalog: the catalog has too many presets."]
    many["presets"].pop()
    assert errors(many) == []


def test_unexpected_fields_are_warned_about_not_rejected():
    """The contract has Understeer ignore unknown keys; here they only
    warn, as they are most likely typos."""
    item = entry()
    item["meta"]["auhtor"] = "Typo"
    item["preset"]["folder"] = "Mine"
    item["extra"] = 1
    errs, warnings = check(dict(catalog(item), comment="x"))
    assert errs == []
    assert warnings == [
        'Catalog: unknown key "comment" is ignored by Understeer; is it a typo?',
        'Preset 1 (test-preset): unknown key "extra" is ignored by Understeer; is it a typo?',
        'Preset 1 (test-preset), meta: unknown key "auhtor" is ignored by Understeer; is it a typo?',
        'Preset 1 (test-preset), preset: unknown key "folder" is ignored by Understeer; is it a typo?']


def test_unknown_keys_are_shown_escaped():
    """A key can hold any text: a line break in it must not start a line of
    its own in the output (in CI, such a line could be a workflow command)."""
    item = entry()
    item["meta"]["x\n::error::fake"] = 1
    _errs, warnings = check(catalog(item))
    assert warnings == ['Preset 1 (test-preset), meta: unknown key '
                        '"x\\n::error::fake" is ignored by Understeer; is '
                        'it a typo?']


@pytest.mark.parametrize("key, value", [
    ("description", "See https://example.org"),
    ("description", "www.example.org"),
    ("game", "file:///home/user/x"),
    ("author", "ftp://x"),
])
def test_no_web_addresses(key, value):
    assert errors(catalog(entry(**{key: value}))) == [
        f"Preset 1 (test-preset): meta.{key} must not contain a web address."]


def test_bad_entry_does_not_hide_the_others():
    bad = entry("bad")
    bad["preset"]["values"] = {"FF": 500}
    errs = errors(catalog(entry("good"), bad, entry("also-good", game="")))
    assert errs == [
        "Preset 2 (bad): preset.values.FF is out of range or no number.",
        "Preset 3 (also-good): meta.game is required and must not be empty."]


def test_validate_leaves_the_data_alone():
    data = catalog(entry())
    before = copy.deepcopy(data)
    check(data)
    assert data == before


# --- the command ---------------------------------------------------------------

def test_command_exit_codes(tmp_path, capsys):
    good = tmp_path / "good.json"
    good.write_text(json.dumps(catalog(entry())))
    assert vc.main([str(good)]) == 0
    assert capsys.readouterr().out.endswith("OK.\n")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(catalog(entry(author=None))))
    assert vc.main([str(bad)]) == 1
    out = capsys.readouterr().out
    assert "error: Preset 1 (test-preset): meta.author is required" in out
    assert "1 problem(s), not ready to publish." in out


def test_command_without_understeer(tmp_path, capsys):
    assert vc.main([str(REPO / "catalog.json"), "--understeer",
                    str(tmp_path)]) == 2
    assert "No Understeer checkout" in capsys.readouterr().err


def test_command_without_catalog(tmp_path, capsys):
    assert vc.main([str(tmp_path / "missing.json")]) == 2
    assert "error:" in capsys.readouterr().err
