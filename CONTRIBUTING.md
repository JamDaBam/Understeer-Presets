# Contributing a preset

Thanks for sharing your setup! A submission is a pull request that adds
one entry to [`catalog.json`](catalog.json). It is reviewed before it is
published.

By submitting, you agree that your entry, including its description, is
published under [CC0 1.0 Universal](LICENSE), and you confirm that it is
yours to give: anyone may then use, change and share it without asking.
Your author name stays in the catalog all the same.

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

## Automatic checks

A community submission is preset data only: **it may change
`catalog.json` and nothing else.** A pull request that adds, changes,
renames or deletes any other file (scripts, tests, workflows,
documentation, anything) fails the check, whatever the change is. If
something else in this repository should change, open an issue instead;
maintainers make such changes themselves, in a separate, reviewed step.

Every pull request to `main` is checked automatically by GitHub Actions
(the check "Validate presets"); `main` is checked again after a merge.
The check runs the same validation as step 5, so a failing check means
the same `error:` lines you get locally: they name the preset (its
position and id) and what to fix. Fix `catalog.json`, push to the same
branch, and the check runs again.

The check also lists the presets the pull request adds, changes or
removes. A removed preset and a preset that seems to have moved to
another id are marked for a maintainer's review; they aren't errors, but
they are looked at closely.

A passing check doesn't mean the preset is accepted: every submission is
reviewed by a maintainer before it is merged. Your entry is published
under CC0 1.0 as said above, only after it is merged. The catalog stays
untrusted input for Understeer as well: it checks every preset again
when it reads the catalog, and adding a preset never applies it to a
wheelbase; only you do, in Understeer.

How the check stays safe: a pull request is treated as untrusted data.
From it, only `catalog.json` is read, without checking out anything of
the pull request; the checking code (`scripts/`, `tests/`) and the CI
requirements come from `main`, the catalog rules from a fixed Understeer
commit (see below), and nothing of the pull request is run. The workflow
can only read the repository and gets no secrets; it doesn't merge,
publish or deploy anything.

## For maintainers

**What the check can't guarantee.** For pull requests, GitHub runs the
workflow file as the pull request has it. A pull request that changes
`.github/workflows/` can therefore change its own check, up to making it
pass, under the same job name "validate"; a required status check can't
tell. Everything the check enforces (only `catalog.json` changes, the
catalog rules, trusted code and parser) only holds while the workflow
that runs is the one on `main`. So before merging:

1. Look at *Files changed*: a community pull request must list
   `catalog.json` only. GitHub shows this list independently of any
   workflow. Anything else: don't merge it as a submission.
2. For a check the pull request can't influence, run the workflow by
   hand: *Actions → Validate presets → Run workflow*, branch `main`,
   with the pull request's number. It uses the workflow, scripts and
   parser of `main` and reads only the pull request's merge, as data.
   Its log names the pull request head it checked; merge only if that
   is still the head of the pull request.
3. Approve workflow runs of pull requests from forks only after looking
   at their changes (see the settings below).

**Maintenance changes** (scripts, tests, workflows, the parser pin, CI
requirements, documentation) are not community submissions, and the
check refuses them like any other change outside `catalog.json`. Make
them on a branch of this repository, in a pull request of their own;
the rest of the check (tests, catalog) still has to pass. Review the
whole diff, run `python3 -m pytest tests` locally against the pinned
Understeer commit, then merge by bypassing the failed rule ("Merge
without waiting for requirements to be met"), which only the bypass list
of the ruleset allows. After the merge, the check runs on `main` with
the new code.

**Trusted parser.** The catalog rules are Understeer's
`understeer/library.py`, fetched at the commit in
[`.github/understeer-parser.txt`](.github/understeer-parser.txt). To
update it, after the change in Understeer is reviewed and public:

1. Put the full 40-character commit id into the `commit=` line.
2. Run the check and the tests locally against a checkout of exactly that
   commit (`--understeer PATH`, or `UNDERSTEER_SRC=PATH python3 -m pytest
   tests`).
3. Change it as a maintenance change (above).

Choose a commit that stays reachable on Understeer's `main` (or a tag):
a commit only on a branch that is later rebased or deleted can't be
fetched any more.

**pytest for CI** is pinned with hashes in
[`.github/requirements-ci.txt`](.github/requirements-ci.txt) and only used
by the workflow.

**Repository settings** (Settings on GitHub; they can't be set from this
repository):

- *Rules → Rulesets*, a branch ruleset for the default branch (`main`),
  enforcement "Active": restrict deletions, block force pushes, require
  a pull request before merging, and require the status check
  "validate", with "GitHub Actions" as its source. The check can be
  chosen once it has run on GitHub at least once. As the only
  maintainer you can't approve your own pull requests, so require no
  approvals. Bypass list: only "Repository admin", set to "For pull
  requests only", for maintenance changes.
- *Actions → General → Actions permissions*: allow only actions of this
  repository's owner, or none from elsewhere; the workflow uses none.
- *Actions → General → Approval for running fork pull request
  workflows*: "Require approval for all external contributors", so a
  workflow from a fork only runs after you have looked at its changes.
- *Actions → General → Workflow permissions*: "Read repository contents
  and packages permissions"; leave "Allow GitHub Actions to create and
  approve pull requests" off.
- *Pages* stays as it is: deploy from branch `main`, folder `/ (root)`.
