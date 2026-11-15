#!/usr/bin/env python3
"""Make sure a community contribution changes catalog.json only.

    git diff --raw -z --no-abbrev -r --find-renames --find-copies-harder \\
        BASE MERGE > changes.bin
    python3 scripts/check_changed_files.py changes.bin [--github]

A community contribution is preset data: the one change it may make is to
modify the content of the existing catalog.json, which stays a regular,
non-executable file. Anything else is refused, whatever the file name or
extension: adding, deleting, renaming or copying a file, changing a file
other than catalog.json, and changing the type or mode of catalog.json
(symbolic link, executable, submodule). Changes to the repository itself
(checking code, workflows, documentation) go through a maintainer's
separate review instead.

The input is git's raw diff with NUL-separated fields, so every path is
read exactly as git has it. Input this script doesn't understand is
refused as well. Exit code 0: data only, 1: other changes, 2: the check
couldn't run. Paths are shown escaped, so they can't become a line of
their own (or a workflow command).
"""
import argparse
import json
import pathlib
import re
import sys

ALLOWED_PATH = "catalog.json"
REGULAR_FILE = "100644"
MAX_SHOWN = 50
# ":<old mode> <new mode> <old id> <new id> <status>", ids as full hashes
HEADER_RE = re.compile(
    r":([0-7]{6}) ([0-7]{6}) ([0-9a-f]{40}|[0-9a-f]{64}) "
    r"([0-9a-f]{40}|[0-9a-f]{64}) ([ACDMRTUX])([0-9]{0,3})")
TWO_PATHS = {"R", "C"}
STATUS_TEXT = {"A": "adds", "C": "copies", "D": "deletes", "M": "modifies",
               "R": "renames", "T": "changes the type of",
               "U": "leaves unmerged", "X": "changes in an unknown way"}


class FormatError(Exception):
    """The input isn't git's raw diff as expected."""


def shown(path):
    """A path from a contribution, safe to print: as a JSON string."""
    return json.dumps(path, ensure_ascii=False)


def parse(raw):
    """[(status, old_mode, new_mode, [paths])] from `git diff --raw -z`."""
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    changes, i = [], 0
    while i < len(fields):
        m = HEADER_RE.fullmatch(fields[i].decode("ascii", "replace"))
        if not m:
            raise FormatError(f"unexpected diff line {i + 1}")
        old_mode, new_mode, _old, _new, status, _score = m.groups()
        count = 2 if status in TWO_PATHS else 1
        paths = fields[i + 1:i + 1 + count]
        if len(paths) != count or not all(paths):
            raise FormatError(f"missing path after diff line {i + 1}")
        changes.append((status, old_mode, new_mode,
                        [p.decode("utf-8", "replace") for p in paths]))
        i += 1 + count
    return changes


def problems(changes):
    """Readable reasons why changes aren't a data-only contribution."""
    out = []
    for status, old_mode, new_mode, paths in changes:
        names = " to ".join(shown(p) for p in paths)
        if paths != [ALLOWED_PATH]:
            out.append(f"The contribution {STATUS_TEXT[status]} {names}: "
                       f"only {ALLOWED_PATH} may change.")
        elif status != "M":
            out.append(f"The contribution {STATUS_TEXT[status]} {names}: "
                       f"{ALLOWED_PATH} may only get new content.")
        elif old_mode != REGULAR_FILE or new_mode != REGULAR_FILE:
            out.append(f"The contribution changes the file mode of {names} "
                       f"from {old_mode} to {new_mode}: it must stay a "
                       "regular, non-executable file.")
    return out


def _annotation(text):
    return (text.replace("%", "%25").replace("\r", "%0D")
            .replace("\n", "%0A"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("diff", help="output of git diff --raw -z")
    parser.add_argument("--github", action="store_true")
    args = parser.parse_args(argv)
    try:
        changes = parse(pathlib.Path(args.diff).read_bytes())
    except (OSError, FormatError) as e:
        print(f"error: can't read the changed files: {e}", file=sys.stderr)
        return 2
    found = problems(changes)
    for line in found[:MAX_SHOWN]:
        print(f"::error title=Data-only contribution::{_annotation(line)}"
              if args.github else f"error: {line}")
    if len(found) > MAX_SHOWN:
        print(f"error: ... and {len(found) - MAX_SHOWN} more changes.")
    if found:
        print(f"Only {ALLOWED_PATH} may change in a community contribution. "
              "Changes to anything else go through a maintainer's review "
              "(see CONTRIBUTING.md).")
        return 1
    print(f"Data only: {'catalog.json changes' if changes else 'no file changes'}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
