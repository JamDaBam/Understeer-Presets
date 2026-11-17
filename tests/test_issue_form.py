"""Tests of the issue form for preset submissions
(.github/ISSUE_TEMPLATE/community-preset.yml): its structure as GitHub's
form schema describes it, its fields and their ids (which Understeer may
use to fill them in), the acknowledgement, and that it matches the catalog
rules. The form is only read as data, with yaml.safe_load. They need PyYAML
and an Understeer checkout, no device and no network."""
import ast
import json
import pathlib
import re
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
FORM = REPO / ".github" / "ISSUE_TEMPLATE" / "community-preset.yml"
sys.path.insert(0, str(REPO / "scripts"))
import validate_catalog as vc  # noqa: E402

try:
    UNDERSTEER = vc.understeer_path()
    LIBRARY = vc.load_library(UNDERSTEER)
except vc.SetupError as e:
    pytest.exit(str(e), returncode=2)

# GitHub's form schema: the keys each part may have
TOP_KEYS = {"name", "description", "title", "labels", "assignees", "projects",
            "type", "body"}
ELEMENT_KEYS = {"type", "id", "attributes", "validations"}
ATTRIBUTES = {
    "markdown": {"value"},
    "input": {"label", "description", "placeholder", "value"},
    "textarea": {"label", "description", "placeholder", "value", "render"},
    "dropdown": {"label", "description", "multiple", "options", "default"},
    "checkboxes": {"label", "description", "options"},
    "upload": {"label", "description"},
}
VALIDATIONS = {
    "markdown": set(),
    "input": {"required", "min_length"},
    "textarea": {"required", "min_length"},
    "dropdown": {"required"},
    "checkboxes": {"required"},
    "upload": {"required", "accept"},
}
ID_RE = re.compile(r"[A-Za-z0-9_-]+")
# The ids are the names of the URL parameters that fill the fields in:
# they must stay as they are
FIELD_IDS = ["preset-name", "game", "wheelbase", "author", "description",
             "tags", "catalog-id", "preset-json", "acknowledgement"]
SENSITIVE = re.compile(r"\b(e-?mail|serial|password|user ?name|hostname|"
                       r"paths?|logs?|diagnos\w*|token|ip)\b")
REQUIRED = {"preset-name", "game", "wheelbase", "author", "description",
            "preset-json", "acknowledgement"}


@pytest.fixture(scope="module")
def form():
    return yaml.safe_load(FORM.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def fields(form):
    return {e["id"]: e for e in form["body"] if "id" in e}


def text_of(element):
    attributes = element["attributes"]
    parts = [attributes.get(k, "") for k in ("label", "description", "value")]
    parts += [o["label"] for o in attributes.get("options", ())
              if isinstance(o, dict)]
    return "\n".join(str(p) for p in parts)


# --- 1./2. YAML and GitHub's form schema ----------------------------------------

def test_plain_yaml_without_tags():
    """Only plain data: no YAML tags, so nothing could be constructed."""
    raw = FORM.read_text(encoding="utf-8")
    assert "!!" not in raw and not re.search(r"(^|\s)!\w", raw)
    assert "\t" not in raw


def test_top_level(form):
    assert set(form) <= TOP_KEYS
    assert all(isinstance(k, str) for k in form)        # no "on:" read as True
    for key in ("name", "description"):
        assert isinstance(form[key], str) and form[key].strip()
    assert isinstance(form["body"], list) and form["body"]
    assert isinstance(form["title"], str)
    assert form["labels"] == ["preset-submission"]


def test_elements_follow_the_schema(form):
    for element in form["body"]:
        kind = element["type"]
        assert set(element) <= ELEMENT_KEYS, element
        assert kind in ATTRIBUTES, kind
        attributes = element["attributes"]
        assert isinstance(attributes, dict) and set(attributes) <= ATTRIBUTES[kind]
        assert set(element.get("validations", {})) <= VALIDATIONS[kind]
        for key, value in attributes.items():
            if key in ("label", "description", "placeholder", "value", "render"):
                assert isinstance(value, str) and value.strip(), (kind, key)
        if kind == "markdown":
            assert "id" not in element and "value" in attributes
        else:
            assert isinstance(attributes.get("label"), str)
            assert ID_RE.fullmatch(element.get("id", "")), element
        for value in element.get("validations", {}).values():
            assert isinstance(value, bool)
    assert any(e["type"] != "markdown" for e in form["body"])


def test_labels_are_distinct(form):
    def normalised(label):
        return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    labels = [e["attributes"]["label"] for e in form["body"] if e["type"] != "markdown"]
    for element in form["body"]:
        if element["type"] == "checkboxes":
            labels += [o["label"] for o in element["attributes"]["options"]]
    assert len({normalised(label) for label in labels}) == len(labels)


# --- 3./4. required fields and stable ids -----------------------------------------

def test_field_ids_are_stable_and_unique(form):
    ids = [e["id"] for e in form["body"] if "id" in e]
    assert ids == FIELD_IDS


def test_required_fields(fields):
    for field_id, element in fields.items():
        required = element.get("validations", {}).get("required", False)
        assert required == (field_id in REQUIRED), field_id


def test_field_types(fields):
    """Fields Understeer may fill in are inputs or textareas: GitHub fills
    those from URL parameters, not drop-downs."""
    kinds = {i: e["type"] for i, e in fields.items()}
    assert kinds == {"preset-name": "input", "game": "input",
                     "wheelbase": "input", "author": "input",
                     "description": "textarea", "tags": "input",
                     "catalog-id": "input", "preset-json": "textarea",
                     "acknowledgement": "checkboxes"}


# --- 5. the JSON field --------------------------------------------------------------

def test_json_field(fields):
    """The field keeps its id, required status and JSON rendering; only its
    label says that it holds the catalog entry now."""
    element = fields["preset-json"]
    attributes = element["attributes"]
    assert attributes["label"] == "Catalog Entry (JSON)"
    assert attributes["render"] == "json"       # shown as code, never as Markdown
    assert element["validations"]["required"] is True
    description = " ".join(attributes["description"].split())
    # Both forms are accepted: the complete entry, and the preset only
    assert "complete catalog entry generated by Understeer" in description
    assert "id, meta and preset" in description
    assert "older version of Understeer" in description
    assert "original preset JSON is also accepted" in description
    assert "Copy as JSON" in description
    assert "understeer_preset, name and values" in description
    assert "example only, not a recommended setup" in description
    # The example is a complete catalog entry
    example = json.loads(attributes["placeholder"])
    assert set(example) == {"id", "meta", "preset"}
    assert set(example["preset"]) == {"understeer_preset", "name", "values"}


def test_json_example_is_marked_as_an_example(fields):
    example = json.loads(fields["preset-json"]["attributes"]["placeholder"])
    assert "Example only" in example["meta"]["description"]
    assert "not a recommended setup" in example["meta"]["description"]


def test_json_example_is_two_space_json(fields):
    """Written as Understeer writes an entry: JSON with two spaces."""
    text = fields["preset-json"]["attributes"]["placeholder"]
    example = json.loads(text)
    assert text == json.dumps(example, indent=2, ensure_ascii=False) + "\n"


def test_json_contract_is_documented():
    contributing = " ".join((REPO / "CONTRIBUTING.md").read_text(
        encoding="utf-8").split())
    assert ("The field *Catalog Entry (JSON)* (id `preset-json`) holds one "
            "of two forms") in contributing
    assert ('**A complete catalog entry** (`{"id": …, "meta": …, '
            '"preset": …}`, see step 2)') in contributing
    assert ('**Only the preset**, from older versions of Understeer or '
            'pasted by hand: the preset as Understeer copies it '
            '(`{"understeer_preset": 1, "name": …, "values": {…}}`)') in contributing
    assert "copy the whole object into the `\"presets\"` list" in contributing


def test_review_rules_are_documented():
    contributing = " ".join((REPO / "CONTRIBUTING.md").read_text(
        encoding="utf-8").split())
    for part in ("Everything in a submission is untrusted data, also a "
                 "complete entry",
                 "The readable fields of the issue must agree with the "
                 "catalog entry",
                 "ask the submitter in the issue which is meant; don't "
                 "decide it yourself",
                 "Never change submitted settings or values silently",
                 "Choose the final, unique id against the current catalog",
                 "`python3 scripts/validate_catalog.py` must pass before "
                 "the entry is published",
                 "Nothing is published automatically",
                 "nothing of a submission is ever applied to a wheelbase",
                 "*Catalog Entry (JSON)* keeps the id `preset-json`"):
        assert part in contributing, part


def test_json_example_is_a_valid_submission(fields):
    """The example entry passes the catalog rules and agrees with the
    examples of the other fields, as a submission must."""
    def example(field_id):
        return fields[field_id]["attributes"]["placeholder"]
    entry = json.loads(example("preset-json"))
    raw = json.dumps({"understeer_library": 1, "presets": [entry]}).encode()
    errors, warnings = vc.validate(raw, LIBRARY)
    assert errors == [] and warnings == []
    catalog = LIBRARY.parse_catalog(raw)
    assert catalog.skipped == [] and len(catalog.entries) == 1
    got = catalog.entries[0]
    assert not got.unsupported and not got.adjusted
    assert got.values == entry["preset"]["values"]      # nothing fitted
    meta = entry["meta"]
    assert entry["id"] == example("catalog-id")
    assert entry["preset"]["name"] == example("preset-name")
    assert meta["game"] == example("game")
    assert meta["wheelbase"] == example("wheelbase")
    assert meta["author"] == example("author")
    assert meta["tags"] == [t.strip() for t in example("tags").split(",")]
    assert meta["drive"] in LIBRARY.DRIVES and "torque_nm" not in meta


def test_legacy_preset_example_is_still_valid(fields):
    """A preset-only submission of an older Understeer, built into an entry
    with the examples of the other fields as before, passes the rules."""
    def example(field_id):
        return fields[field_id]["attributes"]["placeholder"]
    preset = json.loads(example("preset-json"))["preset"]
    entry = {"id": example("catalog-id"),
             "meta": {"author": "Tester", "game": example("game"),
                      "wheelbase": example("wheelbase"),
                      "description": example("description"),
                      "tags": [t.strip() for t in example("tags").split(",")]},
             "preset": preset}
    raw = json.dumps({"understeer_library": 1, "presets": [entry]}).encode()
    errors, warnings = vc.validate(raw, LIBRARY)
    assert errors == [] and warnings == []


def test_description_is_shown_as_text(fields):
    assert fields["description"]["attributes"]["render"] == "text"


# --- 6. acknowledgement ------------------------------------------------------------

def test_acknowledgement(fields):
    element = fields["acknowledgement"]
    options = element["attributes"]["options"]
    assert len(options) == 5 and all(o["required"] is True for o in options)
    text = " ".join(o["label"] for o in options).lower()
    for part in ("public", "personal information", "maintainer reviews",
                 "decline", "change the proposed id", "not tested",
                 "own risk", "cc0"):
        assert part in text, part


def test_notice(form):
    notice = form["body"][0]
    assert notice["type"] == "markdown"
    text = notice["attributes"]["value"].lower()
    for part in ("only for submitting one preset", "everything you enter here "
                 "is public", "github account", "not published automatically",
                 "may ask for changes or decline", "suggestion only",
                 "nobody tests the values", "don't enter anything personal",
                 "only make sure fields are filled in"):
        assert part in text, part


# --- 7. nothing sensitive is asked for ---------------------------------------------

def test_no_sensitive_data_is_asked_for(form):
    for element in form["body"]:
        assert element["type"] != "upload"
        if element["type"] in ("markdown", "checkboxes"):
            continue                    # these say what not to enter
        text = text_of(element).lower()
        assert not SENSITIVE.search(text), (element["id"], SENSITIVE.search(text))
        assert "address" not in text.replace("no web addresses", "")
        assert "value" not in element["attributes"]     # nothing filled in


def test_author_is_not_the_github_account(fields):
    text = fields["author"]["attributes"]["description"]
    assert "doesn't have to be your GitHub name" in text
    assert "not\nput in its place" in text or "not put in its place" in text


# --- 8. the catalog rules -------------------------------------------------------------

def _wheel_bases():
    """The names in Understeer's device.WHEEL_BASES, read from its source as
    a literal, without running it."""
    tree = ast.parse((UNDERSTEER / "understeer" / "device.py").read_text(
        encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", None) == "WHEEL_BASES" for t in node.targets):
            return set(ast.literal_eval(node.value).values())
    raise AssertionError("WHEEL_BASES not found")


def test_wheelbases_are_understeers(fields):
    text = " ".join(fields["wheelbase"]["attributes"]["description"].split())
    listed = text.split("exactly as one of: ")[1].rstrip(".").split(", ")
    assert set(listed) == _wheel_bases() and len(listed) == len(_wheel_bases())
    assert fields["wheelbase"]["attributes"]["placeholder"] in listed


@pytest.mark.parametrize("field_id, limit", [
    ("preset-name", "up to 80 characters"),
    ("game", f"up to {LIBRARY.MAX_GAME} characters"),
    ("author", f"up to {LIBRARY.MAX_AUTHOR} characters"),
    ("description", f"up to {LIBRARY.MAX_DESCRIPTION_LINES} lines and "
                    f"{LIBRARY.MAX_DESCRIPTION} characters"),
    ("tags", f"Up to {LIBRARY.MAX_TAGS} short words of a-z, 0-9 and -"),
    ("catalog-id", "up to 64 characters of\na-z, 0-9 and -"),
])
def test_limits_are_the_catalog_rules(fields, field_id, limit):
    description = fields[field_id]["attributes"]["description"]
    assert " ".join(limit.split()) in " ".join(description.split())


def test_name_limit_is_understeers():
    assert LIBRARY.sharing.MAX_NAME == 80


def test_example_id_follows_the_id_rule(fields):
    assert LIBRARY.ID_RE.fullmatch(fields["catalog-id"]["attributes"]["placeholder"])


# --- 9. no automation, nothing run ------------------------------------------------------

def _workflows():
    for path in sorted((REPO / ".github" / "workflows").glob("*.y*ml")):
        yield path, yaml.safe_load(path.read_text(encoding="utf-8"))


def test_no_workflow_reacts_to_issues():
    for path, workflow in _workflows():
        triggers = workflow.get("on", workflow.get(True))     # "on" reads as True
        names = set(triggers) if isinstance(triggers, (dict, list)) else {triggers}
        assert not names & {"issues", "issue_comment", "pull_request_target",
                            "workflow_run"}, path.name
        assert workflow["permissions"] == {"contents": "read"}, path.name
        assert "ISSUE_TEMPLATE" not in path.read_text(encoding="utf-8")


def test_issue_template_folder_holds_only_forms():
    files = sorted(p.name for p in FORM.parent.iterdir())
    assert files == ["community-preset.yml"]


# --- 10. documentation ------------------------------------------------------------------

def test_documentation():
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "issues/new?template=community-preset.yml" in contributing
    assert "community-preset.yml" in readme
    for text in (contributing, readme):
        text = " ".join(text.split())
        # Sharing from Understeer is there since 2.4.0-beta.1; the coming
        # beta.2 is not described as released
        assert "not available yet" not in text
        assert "*Share → Share with Community…*" in text \
            or "**Share → Share with Community…**" in text
        assert "starting with Understeer 2.4.0-beta.1" in text.replace(
            "Starting", "starting")
        assert "Understeer 2.4.0-beta.1 puts the preset JSON into" in text
        assert ("the coming 2.4.0-beta.2 will put the complete catalog "
                "entry there") in text
        assert "Both formats are accepted." in text
        assert "submit it yourself" in text
        # Who needs an account, and that nothing is published right away
        assert ("Submitting needs a GitHub account; browsing and importing "
                "presets in Understeer doesn't") in text
        assert "reviewed by a maintainer before it" in text
        assert "not published right away" in text \
            or "nothing is published right away" in text
        assert "without a new release of Understeer" in text
    readme_text = " ".join(readme.split())
    for stale in ("not released yet", "not merged yet", "Until the preset "
                  "library is merged"):
        assert stale not in readme_text, stale
    # The rule for pull requests stays
    assert "**it may change\n`catalog.json` and nothing else.**" in contributing
