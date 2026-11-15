# Contributing a preset

Thanks for sharing your setup! A submission is a pull request that adds
one entry to [`catalog.json`](catalog.json). It is reviewed before it is
published.

## 1. Export the preset from Understeer

In Understeer, open the ⋮ menu of the preset under **Saved Presets** and
choose **Share → Copy as JSON** (German: **Teilen → Als JSON kopieren**).
You get something like:

```json
{
  "understeer_preset": 1,
  "name": "GT3 Endurance",
  "values": {"SEN": 540, "FF": 75, "FOR": 100}
}
```

Leave out `"folder"` if it is there: the catalog doesn't decide anyone's
folders. Don't change the values by hand.

## 2. Add the community information

Put the exported preset under `"preset"` and add `"meta"`:

```json
{
  "id": "acc-gt3-endurance",
  "meta": {
    "author": "Your Name",
    "game": "Assetto Corsa Competizione",
    "wheelbase": "CSL DD",
    "drive": "direct_drive",
    "torque_nm": 8,
    "description": "Calm GT3 feel for long stints.",
    "tags": ["gt3", "endurance"]
  },
  "preset": { "...": "the exported preset" }
}
```

| Field | Required | What to write |
| --- | --- | --- |
| `author` | yes | The name you want to be shown, up to 40 characters. |
| `game` | yes | The game, up to 80 characters. |
| `wheelbase` | yes | The wheelbase you made it on, as Understeer shows it, e.g. `CSL DD`, `ClubSport Wheel Base V2.5`, `Podium Wheel Base DD1`. |
| `drive` | no | `belt` or `direct_drive`. |
| `torque_nm` | no | Peak torque of the wheelbase in Nm, a whole number. |
| `description` | no | Plain text, up to 20 lines and 1000 characters. |
| `tags` | no | Up to 10 short words of `a-z`, `0-9` and `-`. |

Texts are shown as plain text. Web addresses aren't allowed in any of
them, and please don't add anything personal beyond the name you choose.

## 3. Choose an id

The `id` names the entry for good; it doesn't change when the preset is
updated later. Use `<game>-<preset name>` in lower case, words joined with
`-`, e.g. `acc-gt3-endurance`. If it is taken, add your name:
`acc-gt3-endurance-alex`. Allowed are `a-z`, `0-9` and `-`, up to 64
characters, not starting or ending with `-`.

## 4. Add it to catalog.json

Add your entry at the end of the `"presets"` list. Keep the file valid
JSON: a comma between entries, none after the last one.

## 5. Validate

```sh
python3 scripts/validate_catalog.py
```

(See the [README](README.md) for what it needs.) Fix every `error:` line
it prints until it ends with `OK.`. A `warning:` about an unknown key
usually means a typo in a field name.

A submission must pass without errors. In particular:

- `author`, `game` and `wheelbase` are filled in,
- the `id` is not used yet,
- every setting is one Understeer knows, with a value it accepts,
- no value is changed by Understeer, e.g. `905` for the steering angle,
  which Understeer would keep as `900`.

## 6. Open a pull request

Fork this repository, commit your change to `catalog.json` on a new
branch and open a pull request. Say in a sentence what the preset is for.
Maintainers review every submission before it is published; they may ask
for changes or decline presets that look unsafe or unhelpful.
