#!/usr/bin/env python3
"""Tell what a contribution changes compared to the published catalog.

    python3 scripts/compare_catalogs.py BASE NEW [--understeer PATH]
                                         [--github]

BASE is the catalog on main, NEW the one of the contribution. It lists
presets added, changed and removed, by id. Ids are stable: an id that
disappears, or a preset that looks moved to another id, needs a maintainer
to look at it, so it is a warning. Whether NEW is a valid catalog is
checked by validate_catalog.py, whether only catalog.json changes by
check_changed_files.py; not here.

This is policy on top of the catalog rules; it never decides alone. Exit
code 0: compared (warnings or not), 2: the comparison couldn't run.
--github writes the warnings as GitHub Actions annotations and a summary.
Only ids are shown from a contribution: they are plain [a-z0-9-] once
Understeer has accepted them.
"""
import argparse
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import validate_catalog as vc  # noqa: E402

def _entries(raw, library):
    """{id: entry} of the presets Understeer accepts in raw; {} for a
    catalog that can't be read at all."""
    try:
        return {e.id: e for e in library.parse_catalog(raw).entries}
    except library.Error:
        return {}


def compare(base_raw, new_raw, library):
    """(notes, warnings) as readable lines."""
    base, new = _entries(base_raw, library), _entries(new_raw, library)
    notes, warnings = [], []
    added = [i for i in new if i not in base]
    removed = [i for i in base if i not in new]
    changed = [i for i in new if i in base and new[i] != base[i]]
    for i in added:
        notes.append(f"New preset: {i}")
    for i in changed:
        notes.append(f"Changed preset: {i}")
    moved = {}
    for i in removed:
        same = [a for a in added if new[a].fingerprint == base[i].fingerprint
                or new[a].name == base[i].name]
        if same:
            moved[i] = same[0]
            warnings.append(f"Preset id {i} is gone and {same[0]} looks like "
                            "the same preset: ids must stay as they are. A "
                            "maintainer has to check this.")
        else:
            warnings.append(f"Preset {i} is removed. A maintainer has to "
                            "check this.")
    if not notes and not warnings:
        notes.append("No preset changed.")
    return notes, warnings


def _annotation(text):
    """text as the message of a GitHub workflow command."""
    return (text.replace("%", "%25").replace("\r", "%0D")
            .replace("\n", "%0A"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("base")
    parser.add_argument("new")
    parser.add_argument("--understeer", help="path of an Understeer checkout")
    parser.add_argument("--github", action="store_true")
    args = parser.parse_args(argv)
    try:
        library = vc.load_library(vc.understeer_path(args.understeer))
        base_raw = pathlib.Path(args.base).read_bytes()
        new_raw = pathlib.Path(args.new).read_bytes()
    except (vc.SetupError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    notes, warnings = compare(base_raw, new_raw, library)
    for line in notes:
        print(line)
    for line in warnings:
        print(f"::warning title=Maintainer review::{_annotation(line)}"
              if args.github else f"warning: {line}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.github and summary:
        # Ids are plain [a-z0-9-], safe in the Markdown summary
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Catalog changes\n\n")
            f.writelines(f"- {line}\n" for line in notes)
            f.write(f"\n{len(warnings)} point(s) need a maintainer's review."
                    if warnings else "\nNothing needs a special review.")
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
