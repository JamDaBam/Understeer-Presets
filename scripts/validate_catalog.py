#!/usr/bin/env python3
"""Check catalog.json against the rules for public submissions.

The catalog rules themselves live in Understeer (understeer/library.py,
documented in its docs/preset-library.md); this script runs them and adds
what a public submission needs on top. It needs an Understeer source
checkout and nothing else, works offline and never touches a device.

    python3 scripts/validate_catalog.py [catalog.json] [--understeer PATH]

PATH is the Understeer checkout; without it, $UNDERSTEER_SRC, else
../Understeer next to this repository. Exit code 0: fine, 1: the catalog
breaks a rule, 2: the check couldn't run.
"""
import argparse
import json
import os
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REQUIRED_META = ("author", "game", "wheelbase")
TEXT_META = ("author", "game", "wheelbase", "description")
# Keys a catalog may have; others are ignored by Understeer and only warned
# about here, as they are most likely typos.
CATALOG_KEYS = {"understeer_library", "presets"}
ENTRY_KEYS = {"id", "meta", "preset"}
META_KEYS = {"author", "game", "wheelbase", "drive", "torque_nm",
             "description", "tags"}
PRESET_KEYS = {"understeer_preset", "name", "values"}
URL_RE = re.compile(r"[a-z][a-z0-9+.-]*://|www\.", re.IGNORECASE)


class SetupError(Exception):
    """The check can't run, e.g. Understeer isn't found."""


def understeer_path(given=None):
    if given:
        return pathlib.Path(given)
    if os.environ.get("UNDERSTEER_SRC"):
        return pathlib.Path(os.environ["UNDERSTEER_SRC"])
    return REPO.parent / "Understeer"


def load_library(path):
    """understeer.library from the checkout at path."""
    path = pathlib.Path(path).resolve()
    if not (path / "understeer" / "library.py").is_file():
        raise SetupError(
            f"No Understeer checkout with understeer/library.py at {path}. "
            "Pass --understeer PATH or set UNDERSTEER_SRC.")
    sys.path.insert(0, str(path))
    try:
        from understeer import library
    finally:
        sys.path.remove(str(path))
    return library


def _where(pos, entry_id):
    return f"Preset {pos + 1}" + (f" ({entry_id})" if entry_id else "")


def _unknown_keys(data):
    """Warnings for keys the contract doesn't know."""
    warnings = []

    def check(obj, known, where):
        if isinstance(obj, dict):
            for key in sorted(set(obj) - known):
                warnings.append(f"{where}: unknown key \"{key}\" is ignored "
                                "by Understeer; is it a typo?")

    check(data, CATALOG_KEYS, "Catalog")
    for pos, item in enumerate(data.get("presets") or []):
        if not isinstance(item, dict):
            continue
        where = _where(pos, item.get("id") if isinstance(item.get("id"), str) else None)
        check(item, ENTRY_KEYS, where)
        check(item.get("meta"), META_KEYS, where + ", meta")
        check(item.get("preset"), PRESET_KEYS, where + ", preset")
    return warnings


def validate(raw, library):
    """(errors, warnings) of the catalog bytes raw, as readable lines."""
    try:
        catalog = library.parse_catalog(raw)
    except library.Error as e:
        return [f"Catalog: {e}."], []
    errors = [f"{_where(pos, entry_id)}: {reason}."
              for pos, entry_id, reason in catalog.skipped]
    data = json.loads(bytes(raw).decode("utf-8-sig"))     # parsed fine above
    order = [p.get("id") if isinstance(p, dict) else None
             for p in data["presets"]]
    for entry in catalog.entries:
        where = _where(order.index(entry.id), entry.id)
        for key in REQUIRED_META:
            if not getattr(entry.meta, key):
                errors.append(f"{where}: meta.{key} is required and must "
                              "not be empty.")
        for key in TEXT_META:
            if URL_RE.search(getattr(entry.meta, key) or ""):
                errors.append(f"{where}: meta.{key} must not contain a "
                              "web address.")
        if URL_RE.search(entry.name):
            errors.append(f"{where}: preset.name must not contain a web address.")
        if entry.unsupported:
            errors.append(f"{where}: settings Understeer doesn't know: "
                          + ", ".join(entry.unsupported) + ".")
        for attr, shared, kept in entry.adjusted:
            errors.append(f"{where}: {attr} is {shared}, but Understeer "
                          f"would keep {kept}; use {kept}.")
    if not catalog.entries and not errors:
        errors.append("Catalog: there is no preset in it.")
    return errors, _unknown_keys(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalog", nargs="?", default=REPO / "catalog.json",
                        help="the catalog to check (default: catalog.json)")
    parser.add_argument("--understeer", help="path of an Understeer checkout")
    args = parser.parse_args(argv)
    try:
        library = load_library(understeer_path(args.understeer))
        raw = pathlib.Path(args.catalog).read_bytes()
    except (SetupError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    errors, warnings = validate(raw, library)
    for line in warnings:
        print(f"warning: {line}")
    for line in errors:
        print(f"error: {line}")
    if errors:
        print(f"{args.catalog}: {len(errors)} problem(s), not ready to publish.")
        return 1
    print(f"{args.catalog}: OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
