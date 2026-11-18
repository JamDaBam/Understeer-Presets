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


EXAMPLE_PREFIX = "example-"
DEMO_NOTE = "Demonstration entry only"


def demo_problems(item):
    """How item is marked wrongly as a demo, as a list of problems.

    An example (its id starts with "example-") says so wherever it is
    shown: "Demo" in its name, the tag "demo" and the note in its
    description. A real community preset carries neither the tag nor the
    note, so it isn't taken for an example (its name may well contain
    "Demo", as in "Demolition Derby")."""
    meta = item["meta"]
    tagged = "demo" in (meta.get("tags") or [])
    noted = DEMO_NOTE in meta.get("description", "")
    if item["id"].startswith(EXAMPLE_PREFIX):
        marks = {"name": "Demo" in item["preset"]["name"], "tag": tagged,
                 "description": noted}
        return [f"{item['id']}: example without the demo {mark}"
                for mark, present in marks.items() if not present]
    marks = {"tag": tagged, "description": noted}
    return [f"{item['id']}: real preset with the demo {mark}"
            for mark, present in marks.items() if present]


def demo_example(entry_id="example-test-demo", **meta):
    item = entry(entry_id, tags=["example", "demo"],
                 description=DEMO_NOTE + ". Not a recommended setup.", **meta)
    item["preset"]["name"] = "Example Test (Demo)"
    return item


def test_published_examples_are_marked_as_demos():
    data = json.loads((REPO / "catalog.json").read_text(encoding="utf-8"))
    examples = [item for item in data["presets"]
                if item["id"].startswith(EXAMPLE_PREFIX)]
    assert examples, "the catalog has no example to check"
    assert [problem for item in data["presets"]
            for problem in demo_problems(item)] == []


def test_examples_next_to_real_presets():
    real = entry("beamng-allrounder", description="Allrounder for BeamNG",
                 tags=None)
    real["preset"]["name"] = "BeamNG - Allrounder"
    derby = entry("wreckfest-derby", tags=["derby"])
    derby["preset"]["name"] = "Demolition Derby"
    mixed = catalog(demo_example("example-a-demo"), real, derby,
                    demo_example("example-b-demo"))
    assert errors(mixed) == []
    assert [demo_problems(item) for item in mixed["presets"]] == [[]] * 4


@pytest.mark.parametrize("change, problem", [
    (lambda i: i["preset"].update(name="Example Test"), "name"),
    (lambda i: i["meta"].update(tags=["example"]), "tag"),
    (lambda i: i["meta"].pop("tags"), "tag"),
    (lambda i: i["meta"].update(description="Shows the format."),
     "description"),
])
def test_example_without_a_demo_mark(change, problem):
    item = demo_example()
    change(item)
    assert demo_problems(item) == [
        f"example-test-demo: example without the demo {problem}"]


def test_example_without_any_demo_mark():
    assert demo_problems(entry("example-plain")) == [
        "example-plain: example without the demo name",
        "example-plain: example without the demo tag",
        "example-plain: example without the demo description"]


@pytest.mark.parametrize("meta, problems", [
    ({"tags": ["demo"]}, ["tag"]),
    ({"description": DEMO_NOTE + "."}, ["description"]),
    ({"tags": ["example", "demo"], "description": DEMO_NOTE + "."},
     ["tag", "description"]),
])
def test_real_preset_with_demo_marks(meta, problems):
    assert demo_problems(entry("real-preset", **meta)) == [
        f"real-preset: real preset with the demo {mark}" for mark in problems]


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
