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

## Repository catalog and auto-categorisation

`scripts/portfolio.py` is the single source of truth for what each repo is:

1. `CURATED` holds a hand-checked category, one-line description and stack for every
   existing repo. Edit a line there to change how a repo is shown.
2. A repo that is not in `CURATED` (any new repo) is categorised from its topics, name,
   GitHub description and README, and its description is the first real sentence of its
   README. Write a clear first paragraph in a new repo's README and it is listed properly
   within six hours, with no edit here.
3. Empty repos and anything in `HIDE` are left out of the catalog.

Categories: autonomous driving, agentic AI, retrieval and ranking, healthcare, speech and
vision, finance, classical ML, software and web apps, and forks.

`scripts/sync_github_metadata.py` pushes the curated descriptions and category topics to
GitHub itself, so each repo's own page matches the profile. Run it from your Mac with `gh`.

## Inline video

`assets/perception-reel.mp4` is a 21-second captioned cut of the three deck scenes.
GitHub will not play a video referenced by a repo path; it has to be uploaded through the
web editor. Edit `README.md` on github.com, drag the MP4 onto the `VIDEO SLOT` comment under
"Perception deck", and commit. The generated `https://github.com/user-attachments/assets/…`
line plays inline with controls. The GIFs below it stay as the fallback for viewers whose
client does not autoplay video.

## Animated cards (assets/live)

`scripts/visuals.py` draws every card on the profile as an animated SVG, in a dark and a
light version: the six flagship cards, the regression ledger, one tile per category, the
three latest repos and the live telemetry panel. `update_readme.py` regenerates all of them
on every run and commits `assets/live/`, so tiles and the latest-repos row change by
themselves when you create a repo. Each image URL carries a content hash (`?v=…`) so
GitHub's image cache refreshes as soon as a card changes.

To change a flagship card, edit `FLAGSHIPS` in `scripts/visuals.py`; to change the ledger,
edit `LEDGER`. Push, and the README workflow rebuilds within a minute.

The snake under "Live telemetry" is made by Platane/snk inside the README job and saved to
`assets/live/github-snake*.svg` on `main`. The step is allowed to fail: if it does, the last
snake stays on the profile and the run still succeeds.

## Repository cards

"Every repository" is one animated card per repo (`assets/live/repo-*.svg`) under an animated
banner per category (`assets/live/section-*.svg`). Cards are rebuilt on every run and cards
for deleted repos are removed. A card's title comes from `TITLES` in `scripts/portfolio.py`,
or from the repo name for a new repo.

Each card also carries a looping animation for its category and a line of the repo's weekly
commits over the last 12 months, read from GitHub's `stats/commit_activity` endpoint and
cached in `docs/data/activity.json` so a slow API answer never blanks a card.

## Repository explorer

`docs/repos.html` is the interactive version of the catalog, deployed with the deck on
GitHub Pages: search, domain filters, sort, flip cards with an hoverable weekly chart, and a
Galaxy view. It reads `docs/data/repos.json`, so it updates with every README rebuild. Links
can open it pre-filtered: `repos.html#cat=finance`, `#q=pytorch`, `#repo=opendrivefm`,
`#view=galaxy`. Each category banner in the README links to its filtered view.

## Perception deck hosting

`.github/workflows/pages.yml` deploys `docs/` to GitHub Pages on every change and after each
README rebuild. Pages must be set to "GitHub Actions" as its source (Settings, Pages), which
the push script does for you with `gh api`.

## How a new repository gets its category

`update_readme.py` runs every six hours and handles any repo that is not hand-checked in
`CURATED` (`scripts/portfolio.py`), in this order:

1. **GitHub Models reads it.** `scripts/ai_classify.py` sends the repo's name, description,
   topics and README to `openai/gpt-4.1-mini` through GitHub Models, using the workflow's own
   token (the `models: read` permission in `readme.yml`). It picks one of the existing
   categories, or says the repo belongs to a new field and names it, and writes a display
   title, a one-sentence description using only facts from the README, and the stack. The
   answer is cached in `docs/data/auto_meta.json` and refreshed only when the README or
   description changes.
2. **Keyword rules**, if the model is unavailable: topics count 3x, the name 2x, the
   description 2x, the README 1x.
3. **Hidden categories** wake up when a repo needs them: Robotics, Generative media, Language
   AI, Data engineering, MLOps and cloud, Security, Games and simulation, Coursework.
4. **Brand-new categories.** If the model names a new field, or nothing matches and the repo
   has GitHub topics, a new category is created from that name, given its own colour, and
   kept in `docs/data/categories.json` so later repos on the same topic join it. The README
   cards, explorer page and 3D deck all pick it up automatically.

To force a category for a repo, add it to `CURATED`. To make sure a new repo is understood,
give it a clear README first paragraph and a couple of GitHub topics.

## Flagship cards and the contribution city

`scripts/showcase.py` draws the six flagship cards, each as a different picture of how the
system works (camera rig, monitor wall, trajectories, agent pipeline, ranking funnel, noisy
waveform), and the 3D contribution city from the same calendar data as the rest of the page.
No third-party action is involved, so the chart cannot go blank when an outside service fails.

## Why the workflows do not fail

* **Rebuild README** retries every GitHub API call with backoff, reruns the generator up to
  three times, treats the snake as optional, and rebases and retries its push if someone
  pushed meanwhile. If something still cannot be done it leaves a yellow warning on the run
  and keeps the last good profile, instead of a red failure.
* **Deploy perception deck** runs only after a successful rebuild, never cancels a deploy
  half way, and retries the deploy three times, the last time with a freshly packaged
  site, because GitHub Pages occasionally loses the artifact it was just given.
