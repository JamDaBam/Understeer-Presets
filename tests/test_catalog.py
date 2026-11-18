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


NAME_MARK = 'an example needs "Demo" in preset.name'
TAG_MARK = 'an example needs the tag "demo"'
NOTE_MARK = 'an example needs "Demonstration entry only" in meta.description'
REAL_TAG = 'the tag "demo" is for examples only (id "example-…")'
REAL_NOTE = ('"Demonstration entry only" in meta.description is for '
             'examples only (id "example-…")')


def demo_example(entry_id="example-test-demo", **meta):
    """An example marked as the published ones are."""
    meta = {"tags": ["example", "demo"],
            "description": vc.DEMO_NOTE + ". Not a recommended setup.",
            **meta}
    item = entry(entry_id, **meta)
    item["preset"]["name"] = "Example Test (Demo)"
    return item


def real_preset(entry_id="beamng-allrounder", name="BeamNG - Allrounder",
                **meta):
    item = entry(entry_id, **meta)
    item["preset"]["name"] = name
    return item


def test_examples_next_to_real_presets():
    mixed = catalog(demo_example("example-a-demo"),
                    real_preset(description="Allrounder for BeamNG"),
                    real_preset("wreckfest-derby", "Demolition Derby",
                                tags=["derby"]),
                    demo_example("example-b-demo"))
    assert check(mixed) == ([], [])


def test_only_real_presets():
    assert errors(catalog(real_preset("a"), real_preset("b"))) == []


def test_only_examples():
    assert errors(catalog(demo_example("example-a"),
                          demo_example("example-b"))) == []


@pytest.mark.parametrize("name", ["Demolition Derby", "Rally Demo Run",
                                  "demo day"])
def test_demo_in_the_name_of_a_real_preset(name):
    assert errors(catalog(real_preset(name=name))) == []


@pytest.mark.parametrize("change, problem", [
    (lambda i: i["preset"].update(name="Example Test"), NAME_MARK),
    (lambda i: i["preset"].update(name="Example Test (demo)"), NAME_MARK),
    (lambda i: i["meta"].update(tags=["example"]), TAG_MARK),
    (lambda i: i["meta"].pop("tags"), TAG_MARK),
    (lambda i: i["meta"].update(description="Shows the format."), NOTE_MARK),
    (lambda i: i["meta"].pop("description"), NOTE_MARK),
])
def test_example_without_a_demo_mark(change, problem):
    item = demo_example()
    change(item)
    assert errors(catalog(item)) == [
        f"Preset 1 (example-test-demo): {problem}."]


def test_example_without_any_demo_mark():
    assert errors(catalog(entry("example-plain"))) == [
        f"Preset 1 (example-plain): {NAME_MARK}.",
        f"Preset 1 (example-plain): {TAG_MARK}.",
        f"Preset 1 (example-plain): {NOTE_MARK}."]


def test_example_marks_as_understeer_shows_them():
    """The marks count as Understeer cleans and shows them: a tag in
    upper case is the tag "demo", the note split over lines is the
    note."""
    item = demo_example(tags=["DEMO"],
                        description="Demonstration\nentry only.")
    assert errors(catalog(item)) == []


@pytest.mark.parametrize("meta, problems", [
    ({"tags": ["demo"]}, [REAL_TAG]),
    ({"tags": ["Demo", "gt3"]}, [REAL_TAG]),
    ({"description": vc.DEMO_NOTE + "."}, [REAL_NOTE]),
    ({"description": "Fast. demonstration  ENTRY\nonly"}, [REAL_NOTE]),
    ({"description": "Demon\u200bstration entry only"}, [REAL_NOTE]),
    ({"tags": ["example", "demo"], "description": vc.DEMO_NOTE + "."},
     [REAL_TAG, REAL_NOTE]),
])
def test_real_preset_with_demo_marks(meta, problems):
    assert errors(catalog(real_preset(**meta))) == [
        f"Preset 1 (beamng-allrounder): {p}." for p in problems]


def test_real_preset_with_other_tags_and_text():
    item = real_preset(tags=["demolition", "demos", "example"],
                       description="Not a demonstration, an entry only for "
                                   "rallies.")
    assert errors(catalog(item)) == []


@pytest.mark.parametrize("meta, reason", [
    ({"tags": "demo"}, "meta.tags is not a list of at most 10 tags"),
    ({"tags": ["demo", 1]},
     "meta.tags has a tag that is no short word of a-z, 0-9 and -"),
    ({"description": ["Demonstration entry only"]},
     "meta.description is not text"),
])
def test_malformed_metadata_of_an_example(meta, reason):
    """Metadata Understeer can't read leaves the entry out; the error says
    why, and the demo rules don't run on what isn't there."""
    assert errors(catalog(demo_example(**meta))) == [
        f"Preset 1 (example-test-demo): {reason}."]


def test_malformed_meta_object():
    item = demo_example()
    item["meta"] = ["demo"]
    assert errors(catalog(item)) == [
        "Preset 1 (example-test-demo): meta is not an object."]


def test_demo_rules_with_other_errors():
    """The demo rules add to the other errors of an entry; a bad entry
    next to it doesn't hide them."""
    bad = demo_example(author=None)
    bad["preset"]["name"] = "Example"
    errs = errors(catalog(real_preset(tags=["demo"]), bad))
    assert errs == [
        f"Preset 1 (beamng-allrounder): {REAL_TAG}.",
        "Preset 2 (example-test-demo): meta.author is required and must "
        "not be empty.",
        f"Preset 2 (example-test-demo): {NAME_MARK}."]


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


def test_command_checks_the_candidate_catalog(tmp_path, capsys):
    """As in CI: the command checks the catalog it is given (a pull
    request's), not the published one next to it."""
    published = REPO / "catalog.json"
    before = published.read_bytes()
    assert vc.main([str(published)]) == 0
    capsys.readouterr()
    data = json.loads(before)
    wrong = demo_example("example-unmarked")
    wrong["meta"]["tags"] = ["example"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(dict(data, presets=data["presets"] + [wrong])))
    assert vc.main([str(bad)]) == 1
    out = capsys.readouterr().out
    position = len(data["presets"]) + 1
    assert (f"error: Preset {position} (example-unmarked): {TAG_MARK}.\n"
            in out)
    assert "1 problem(s), not ready to publish." in out
    good = tmp_path / "good.json"
    good.write_text(json.dumps(dict(
        data, presets=data["presets"] + [real_preset("acc-allrounder")])))
    assert vc.main([str(good)]) == 0
    assert capsys.readouterr().out.endswith("OK.\n")
    assert published.read_bytes() == before


def test_command_without_understeer(tmp_path, capsys):
    assert vc.main([str(REPO / "catalog.json"), "--understeer",
                    str(tmp_path)]) == 2
    assert "No Understeer checkout" in capsys.readouterr().err


def test_command_without_catalog(tmp_path, capsys):
    assert vc.main([str(tmp_path / "missing.json")]) == 2
    assert "error:" in capsys.readouterr().err
