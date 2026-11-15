"""Tests of the rule that a community contribution changes catalog.json
only. They build small git repositories in a temporary directory; they
need git, but no Understeer checkout, no device and no network."""
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import check_changed_files as ccf  # noqa: E402

GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t",
           "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, env=GIT_ENV).stdout


@pytest.fixture
def repo(tmp_path):
    """A repository like this one, committed as the base."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    (r / "catalog.json").write_text('{"understeer_library": 1, "presets": []}\n')
    (r / "scripts").mkdir()
    (r / "scripts/validate_catalog.py").write_text("print('trusted')\n")
    (r / ".github/workflows").mkdir(parents=True)
    (r / ".github/workflows/validate-presets.yml").write_text("name: x\n")
    (r / ".github/understeer-parser.txt").write_text("commit=0\n")
    (r / ".github/requirements-ci.txt").write_text("pytest==8\n")
    (r / "README.md").write_text("readme\n")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "base")
    return r


def check(repo):
    """problems() of the uncommitted changes in repo, committed."""
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "change")
    raw = git(repo, "diff", "--raw", "-z", "--no-abbrev", "-r",
              "--find-renames", "--find-copies-harder", "HEAD^", "HEAD")
    return ccf.problems(ccf.parse(raw))


def test_catalog_change_is_data_only(repo):
    (repo / "catalog.json").write_text('{"understeer_library": 1, "presets": [1]}\n')
    assert check(repo) == []


def test_no_change_is_data_only(repo):
    assert check(repo) == []


@pytest.mark.parametrize("path", [
    "scripts/new_tool.py", "tests/conftest.py", "run.sh", "Makefile",
    "setup.py", "docs/notes.md", ".github/workflows/other.yml",
    "catalog.json.bak", "presets/catalog.json"])
def test_added_file_is_refused(repo, path):
    (repo / path).parent.mkdir(parents=True, exist_ok=True)
    (repo / path).write_text("anything\n")
    found = check(repo)
    assert len(found) == 1 and found[0].startswith("The contribution adds ")


@pytest.mark.parametrize("path", [
    "scripts/validate_catalog.py", ".github/workflows/validate-presets.yml",
    ".github/understeer-parser.txt", ".github/requirements-ci.txt",
    "README.md"])
def test_modified_file_is_refused(repo, path):
    (repo / path).write_text("changed\n")
    assert check(repo) == [f'The contribution modifies "{path}": only '
                           "catalog.json may change."]


def test_catalog_together_with_code_is_refused(repo):
    (repo / "catalog.json").write_text('{"understeer_library": 1, "presets": [2]}\n')
    (repo / "scripts/validate_catalog.py").write_text("print('ok')\n")
    found = check(repo)
    assert len(found) == 1 and '"scripts/validate_catalog.py"' in found[0]


def test_executable_without_extension_is_refused(repo):
    tool = repo / "tool"
    tool.write_bytes(b"\x7fELF\x02\x01\x01")
    tool.chmod(0o755)
    found = check(repo)
    assert found == ['The contribution adds "tool": only catalog.json may change.']


def test_deleted_file_is_refused(repo):
    (repo / "README.md").unlink()
    assert check(repo) == ['The contribution deletes "README.md": only '
                           "catalog.json may change."]


def test_deleted_catalog_is_refused(repo):
    (repo / "catalog.json").unlink()
    assert check(repo) == ['The contribution deletes "catalog.json": '
                           "catalog.json may only get new content."]


def test_renamed_file_is_refused(repo):
    git(repo, "mv", "README.md", "README.txt")
    assert check(repo) == ['The contribution renames "README.md" to '
                           '"README.txt": only catalog.json may change.']


def test_file_renamed_to_catalog_is_refused(repo):
    (repo / "catalog.json").unlink()
    git(repo, "mv", "README.md", "catalog.json")
    found = check(repo)
    assert found and all("only catalog.json may change" in f
                         or "may only get new content" in f for f in found)


def test_copied_file_is_refused(repo):
    (repo / "scripts/copy.py").write_text("print('trusted')\n")
    assert check(repo) == ['The contribution copies '
                           '"scripts/validate_catalog.py" to "scripts/copy.py": '
                           "only catalog.json may change."]


def test_executable_catalog_is_refused(repo):
    (repo / "catalog.json").chmod(0o755)
    found = check(repo)
    assert found == ['The contribution changes the file mode of '
                     '"catalog.json" from 100644 to 100755: it must stay a '
                     "regular, non-executable file."]


def test_catalog_as_symlink_is_refused(repo):
    (repo / "catalog.json").unlink()
    (repo / "catalog.json").symlink_to("/etc/passwd")
    found = check(repo)
    assert found and "catalog.json" in found[0]


def test_catalog_as_directory_is_refused(repo):
    (repo / "catalog.json").unlink()
    (repo / "catalog.json").mkdir()
    (repo / "catalog.json/x").write_text("x\n")
    found = check(repo)
    assert len(found) == 2


def test_odd_path_is_shown_escaped(repo, tmp_path, capsys):
    name = "x\n::error::forged%0A"
    (repo / name).write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "odd")
    diff = tmp_path / "diff.bin"
    diff.write_bytes(git(repo, "diff", "--raw", "-z", "--no-abbrev", "-r",
                         "HEAD^", "HEAD"))
    assert ccf.main([str(diff), "--github"]) == 1
    out = capsys.readouterr().out.splitlines()
    assert out[0] == ('::error title=Data-only contribution::The contribution '
                      'adds "x\\n::error::forged%250A": only catalog.json '
                      "may change.")
    assert not any(line.startswith("::error::") for line in out)


def test_many_changes_are_cut_short(repo, tmp_path, capsys):
    for i in range(60):
        (repo / f"f{i}").write_text(f"{i}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "many")
    diff = tmp_path / "diff.bin"
    diff.write_bytes(git(repo, "diff", "--raw", "-z", "--no-abbrev", "-r",
                         "HEAD^", "HEAD"))
    assert ccf.main([str(diff)]) == 1
    out = capsys.readouterr().out
    assert out.count("error: The contribution adds") == 50
    assert "... and 10 more changes." in out


@pytest.mark.parametrize("raw", [
    b"catalog.json\0",
    b":100644 100644 " + b"0" * 40 + b" " + b"1" * 40 + b" M\0",
    b":100644 100644 " + b"0" * 40 + b" " + b"1" * 40 + b" R100\0a\0",
    b":100644 100644 abc def M\0catalog.json\0",
])
def test_unexpected_input_is_a_setup_error(tmp_path, raw):
    diff = tmp_path / "diff.bin"
    diff.write_bytes(raw)
    assert ccf.main([str(diff)]) == 2


def test_missing_input_is_a_setup_error(tmp_path):
    assert ccf.main([str(tmp_path / "none")]) == 2
