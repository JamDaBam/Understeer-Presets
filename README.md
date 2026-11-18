# Understeer Presets

Community presets for [Understeer](https://github.com/JamDaBam/Understeer),
the app for tuning Fanatec wheelbases on Linux.

## How it works

The whole library is one static file, [`catalog.json`](catalog.json), with
every preset embedded in it. There is no server, no database, no API and
no account: the catalog is published as a plain file through GitHub Pages
at

https://jamdabam.github.io/Understeer-Presets/catalog.json

Every change merged into `main` appears there within about ten minutes.

Starting with Understeer 2.4.0-beta.1 (a test version), **Community
Library…** on the Presets page downloads only this file, shows the
presets in it and lets you add the ones you choose to your own presets.
Browsing and importing presets needs no account. Because the catalog is
only this file, a preset added here reaches Understeer without a new
release of Understeer.

Each entry holds a preset exactly as Understeer exports it, plus
community information such as the game and the wheelbase it was made on.
The format and its rules are described in Understeer's
[`docs/preset-library.md`](https://github.com/JamDaBam/Understeer/blob/main/docs/preset-library.md).

**Adding a preset never changes your wheelbase.** It is saved as one of
your presets; its settings only reach the wheelbase when you apply it
yourself in Understeer, as with any other preset.

The catalog can hold demonstration entries and community presets.
**Demonstration entries** are marked as such: their id starts with
`example-`, their name says "Demo", they have the tag `demo` and their
description says so. They show the format and are neither tested on a
wheelbase nor recommended settings. **Community presets** come from
their authors and are reviewed by a maintainer before they are
published.

## Validating the catalog

The check uses the catalog rules of Understeer itself, so it needs an
Understeer source checkout with `understeer/library.py` and Python 3. It
runs offline and doesn't touch any device.

```sh
git clone https://github.com/JamDaBam/Understeer.git ../Understeer
python3 scripts/validate_catalog.py
```

It looks for Understeer in `../Understeer`; elsewhere, pass
`--understeer PATH` or set `UNDERSTEER_SRC`. It prints every problem and
ends with exit code 0 when the catalog is ready to publish, 1 when it
isn't and 2 when the check can't run.

The tests of the check need pytest:

```sh
python3 -m pytest tests
```

Pull requests are checked the same way automatically, by GitHub Actions.
A community pull request may change `catalog.json` only; see "Automatic
checks" in [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing

Submit a preset with the
[preset submission form](https://github.com/JamDaBam/Understeer-Presets/issues/new?template=community-preset.yml)
(`.github/ISSUE_TEMPLATE/community-preset.yml`, no Git needed), or as a
pull request that changes `catalog.json` only; see
[CONTRIBUTING.md](CONTRIBUTING.md).

Starting with Understeer 2.4.0-beta.1, **Share → Share with Community…**
in the menu of a saved preset fills in the submission form for you; you
check it on GitHub and submit it yourself. Understeer 2.4.0-beta.1 puts
the preset JSON into the form; 2.4.0-beta.2 and newer put the complete
catalog entry there. Both formats are accepted. Submitting
needs a GitHub account; browsing and importing presets in Understeer
doesn't.

Every submission is reviewed by a maintainer before it is published, also
when its automatic check passes; nothing is published right away.

## License

The catalog and everything in it are dedicated to the public domain under
[CC0 1.0 Universal](LICENSE): anyone may use, change and share the presets
for any purpose, without asking and without having to name anyone.
