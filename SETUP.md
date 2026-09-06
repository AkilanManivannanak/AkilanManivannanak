# Deploying this profile

Everything lives in one repository: `AkilanManivannanak/AkilanManivannanak`. Because the
repo name matches the username, its `README.md` renders on the GitHub profile page.

## 1. Get the files in

```bash
git clone https://github.com/AkilanManivannanak/AkilanManivannanak.git
cd AkilanManivannanak
# copy the contents of this bundle in, then:
git add -A
git commit -m "feat: perception-deck profile"
git push
```

Your profile page should show the animated hero within a minute. GitHub proxies images
through camo, and SMIL/CSS animation inside an SVG survives that proxy, so the hero and
the repo map animate on the live profile.

## 2. Turn on Pages for the 3D deck

Repository → **Settings → Pages → Build and deployment → Source: GitHub Actions**.

Push once more, or run the **Deploy perception deck** workflow by hand. The deck lands at:

```
https://akilanmanivannanak.github.io/AkilanManivannanak/
```

That is the URL the README's launch button already points at. Nothing to edit.

## 3. Create the token the stats need (one minute)

The contributions figure comes from the GraphQL contributions calendar, which the default
`GITHUB_TOKEN` cannot read. Without a token the workflow still runs and every other number
is correct; the contributions badge just reads `n/a`.

1. github.com/settings/tokens → **Generate new token (classic)**
2. Scopes: `repo` and `read:user`
3. Repository → **Settings → Secrets and variables → Actions → New repository secret**
4. Name it `PROFILE_TOKEN`, paste the token

## 4. First run

Actions tab → **Rebuild README** → *Run workflow*. It will:

- fill the `STATS`, `ACTIVITY` and `AUDIT` marker blocks in the README and commit
- publish `contrib-endpoint.json` and friends to an `output` branch, which is what the
  shields.io badges at the top of the README read from

Then run **Isometric contribution graph** once to generate `profile-3d-contrib/`.

After that the schedule takes over: contribution graph 01:15 UTC, README rebuild 05:40 UTC.

## What each piece does

| Path | Purpose |
|---|---|
| `README.md` | The profile page. Marker blocks are machine-maintained; everything else is yours to edit. |
| `assets/hero-*.svg` | Animated BEV instrument, dark and light. Hand-authored, no dependencies. |
| `assets/repo-map-*.svg` | The one-encoder-three-systems diagram. |
| `docs/index.html` | The interactive deck. Single file, three.js from cdnjs, hand-rolled orbit controls. |
| `docs/_body.html` | Source for the deck without the HTML skeleton. Edit here, regenerate `index.html`. |
| `scripts/update_readme.py` | Computes every number and splices the marker blocks. |
| `AGENTS.md`, `llms.txt` | Machine-readable facts, including the gaps. |

## Editing the deck

Repository data lives in the `REPOS` array in `docs/index.html`, one line per repo:
`["name", "domain", size, "note"]`. Domains are `av`, `agentic`, `rank`, `health`,
`signal`, `archive`. Add a repo there and it appears as a node, positioned deterministically
from a hash of its name, and clicking it opens the repo.

To regenerate `index.html` after editing `_body.html`:

```bash
python3 - <<'PY'
body = open('docs/_body.html').read()
i = body.index('<div id="stage">')
open('docs/index.html','w').write(
  '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
  '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
  + body[:i] + '</head>\n<body>\n' + body[i:] + '\n</body>\n</html>\n')
PY
```

## Two things to fix while you are in here

Both were flagged by the repo audit and both weaken the profile the README points at:

1. **34 repositories have no description.** The `AUDIT` block will list them by name after
   the first workflow run. Setting them is an hour of work and it is what makes the repos
   findable at all.
2. **The two `nuscenes-devkit` PRs are still open.** Either nudge them or close them. The
   audit block prints their age in days on your own profile, which is uncomfortable by
   design.
