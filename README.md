# Understeer Presets

Community presets for [Understeer](https://github.com/JamDaBam/Understeer),
the app for tuning Fanatec wheelbases on Linux.

## How it works

The whole library is one static file, [`catalog.json`](catalog.json), with
every preset embedded in it. Understeer downloads only this file, shows
the presets in it and lets you add the ones you choose to your own
presets. There is no server, no database, no API and no account: the
catalog is meant to be published as a plain file through GitHub Pages
(not set up yet).

Each entry holds a preset exactly as Understeer exports it, plus
community information such as the game and the wheelbase it was made on.
The format and its rules are described in Understeer's
[`docs/preset-library.md`](https://github.com/JamDaBam/Understeer/blob/main/docs/preset-library.md).

**Adding a preset never changes your wheelbase.** It is saved as one of
your presets; its settings only reach the wheelbase when you apply it
yourself in Understeer, as with any other preset.

The two presets in the catalog now are **examples only**. They show the
format and are neither tested on a wheelbase nor recommended settings.

## Validating the catalog

The check uses the catalog rules of Understeer itself, so it needs an
Understeer source checkout (one with `understeer/library.py`) and
Python 3. It runs offline and doesn't touch any device.

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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every submission is reviewed
before it is published.

## License

The catalog and everything in it are dedicated to the public domain under
[CC0 1.0 Universal](LICENSE): anyone may use, change and share the presets
for any purpose, without asking and without having to name anyone.
