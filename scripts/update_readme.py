#!/usr/bin/env python3
"""Regenerate the marker blocks in README.md and the shields.io endpoint files.

Everything here is computed from GitHub's own API for the authenticated user, so the
numbers on the profile match what GitHub reports rather than a third-party card's
public-only, calendar-year approximation.

Run locally:   GITHUB_TOKEN=ghp_... python scripts/update_readme.py
In Actions:    see .github/workflows/readme.yml
"""

import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
import hashlib
import time
import html

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import visuals  # noqa: E402
import showcase  # noqa: E402
import ai_classify  # noqa: E402
import portfolio  # noqa: E402

USER = os.environ.get("GH_USER", "AkilanManivannanak")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

DECK = f"https://{USER.lower()}.github.io/{USER}/"

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
HEAD = {
    "Accept": "application/vnd.github+json",
    "User-Agent": f"{USER}-profile-builder",
}
if TOKEN:
    HEAD["Authorization"] = f"Bearer {TOKEN}"


def _request(req, attempts=5):
    """GitHub answers 5xx, 429 or a secondary rate limit now and then. Retry with backoff
    instead of failing the whole run; a 404 or 401 is real and is raised at once."""
    import urllib.error
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if e.code in (401, 404, 410, 422) or i == attempts - 1:
                raise
            wait = int(retry_after) if (retry_after or "").isdigit() else 4 * (2 ** i)
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
            if i == attempts - 1:
                raise
            wait = 4 * (2 ** i)
        print(f"  ! GitHub API hiccup on {req.full_url[:80]}, retrying in {wait}s")
        time.sleep(min(wait, 60))


def get(url):
    return _request(urllib.request.Request(url, headers=HEAD))


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    return _request(urllib.request.Request(GRAPHQL, data=body, headers={**HEAD, "Content-Type": "application/json"}))


# ----------------------------------------------------------------- collection

def all_repos():
    repos, page = [], 1
    while True:
        batch = get(f"{API}/users/{USER}/repos?per_page=100&page={page}&sort=pushed")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


CAL_FRAGMENT = """
fragment Cal on ContributionsCollection {
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
  totalCommitContributions
  totalPullRequestContributions
  totalIssueContributions
  totalPullRequestReviewContributions
}"""


def contribution_windows():
    """Rolling 365 days plus the two previous calendar years, for the deck's year picker."""
    if not TOKEN:
        return None
    now = datetime.now(timezone.utc)
    wins = [("w0", "last 365 days", now - timedelta(days=365), now)]
    for i in (1, 2):
        y = now.year - i
        wins.append((f"w{i}", str(y),
                     datetime(y, 1, 1, tzinfo=timezone.utc),
                     datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc)))

    decl = ", ".join(f"$f{i}:DateTime!, $t{i}:DateTime!" for i in range(len(wins)))
    sel = "\n".join(f"    {k}: contributionsCollection(from:$f{i},to:$t{i}) {{ ...Cal }}"
                     for i, (k, _, _, _) in enumerate(wins))
    q = f"query($login:String!, {decl}) {{ user(login:$login) {{\n{sel}\n  }} }}{CAL_FRAGMENT}"
    variables = {"login": USER}
    for i, (_, _, frm, to) in enumerate(wins):
        variables[f"f{i}"] = frm.isoformat()
        variables[f"t{i}"] = to.isoformat()
    try:
        data = gql(q, variables)
    except Exception as e:  # an expired token or an API outage must not sink the run
        print(f"::warning::Contribution calendar unavailable ({e}); keeping the last saved one.")
        return None
    user = (data.get("data") or {}).get("user") or {}
    if not user:
        return None
    out = []
    for i, (k, label, _, _) in enumerate(wins):
        c = user.get(k)
        if c:
            out.append((label, c))
    return out


def contributions_last_year():
    """The rolling-365-day window, kept as the primary figure for the README."""
    wins = contribution_windows()
    return wins[0][1] if wins else None


def pull_requests():
    try:
        mine = get(f"{API}/search/issues?q=author:{USER}+type:pr&per_page=100")
        items = mine.get("items", [])
    except Exception:
        return {"total": 0, "external": [], "open_external": []}
    external, open_external = [], []
    for it in items:
        repo = it["repository_url"].split("/repos/")[-1]
        if not repo.lower().startswith(USER.lower() + "/"):
            external.append(it)
            if it.get("state") == "open":
                open_external.append((repo, it["number"], it["title"], it["created_at"]))
    return {"total": mine.get("total_count", len(items)), "external": external,
            "open_external": open_external}


# ----------------------------------------------------------------- rendering

def badge(label, message, color="e0873a"):
    return {"schemaVersion": 1, "label": label, "message": message,
            "color": color, "labelColor": "07090c", "style": "flat-square"}


def write_endpoints(user, repos, contrib, prs):
    OUT.mkdir(exist_ok=True)
    stars = sum(r.get("stargazers_count") or 0 for r in repos)
    total = contrib["contributionCalendar"]["totalContributions"] if contrib else None

    files = {
        "contrib-endpoint.json": badge("contributions (365d)",
                                       f"{total:,}" if total is not None else "n/a"),
        "repos-endpoint.json": badge("public repos", str(user.get("public_repos", len(repos)))),
        "stars-endpoint.json": badge("stars earned", str(stars)),
        "prs-endpoint.json": badge("pull requests", str(prs["total"]), "3fb8a6"),
        "followers-endpoint.json": badge("followers", str(user.get("followers", 0)), "3fb8a6"),
    }
    for name, payload in files.items():
        (OUT / name).write_text(json.dumps(payload, indent=2) + "\n")
    return stars, total


def block_stats(user, repos, contrib, stars, total, prs):
    originals = [r for r in repos if not r.get("fork")]
    forks = [r for r in repos if r.get("fork")]
    described = [r for r in repos if (r.get("description") or "").strip()]
    langs = {}
    for r in originals:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top = ", ".join(f"{k} ({v})" for k, v in sorted(langs.items(), key=lambda x: -x[1])[:5])

    rows = [
        ("Public repositories", f"{len(repos)}  ·  {len(originals)} original, {len(forks)} forks"),
        ("Stars earned", str(stars)),
        ("Contributions, rolling 365 days", f"{total:,}" if total is not None else "requires a token"),
        ("Pull requests authored", str(prs["total"])),
        ("Repos carrying a description", f"{len(described)} / {len(repos)}"),
        ("Primary languages", top or "n/a"),
    ]
    out = ["| Signal | Value |", "|---|---|"]
    out += [f"| {a} | {b} |" for a, b in rows]
    out.append("")
    out.append(f"<sub>Recomputed {datetime.now(timezone.utc):%d %b %Y, %H:%M} UTC "
               f"from the GitHub API.</sub>")
    return "\n".join(out)


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


# ----------------------------------------------------------------- repo knowledge
#
# Categories, descriptions and stacks come from scripts/portfolio.py: hand-checked entries
# for existing repos, and each repo's own topics, description and README for new ones.

DOMAIN_ORDER = portfolio.DOMAIN_ORDER
CATALOG_LABELS = portfolio.LABELS
DOMAIN_LABELS = portfolio.LABELS
DOMAIN_ICON = portfolio.ICONS
NEW_DAYS = 30
_README_CACHE = {}


def readme_of(repo):
    """Raw README text of a repo, cached per run. Empty string when there is none."""
    name = repo["name"]
    if name not in _README_CACHE:
        text = ""
        try:
            req = urllib.request.Request(
                f"{API}/repos/{USER}/{name}/readme",
                headers=dict(HEAD, Accept="application/vnd.github.raw"))
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode("utf-8", "replace")
        except Exception:
            text = ""
        _README_CACHE[name] = text
    return _README_CACHE[name]


def classify(repo):
    name = repo["name"]
    if name in portfolio.CURATED or repo.get("fork"):
        return portfolio.classify(repo)
    return portfolio.classify(repo, readme_of(repo))


def describe(repo):
    if repo["name"] in portfolio.CURATED:
        return portfolio.describe(repo)
    return portfolio.describe(repo, readme_of(repo))


ACTIVITY_FILE = ROOT / "docs" / "data" / "activity.json"
ACTIVITY_WEEKS = 52
_ACTIVITY = None
_ACTIVITY_DONE = set()


def _load_activity():
    global _ACTIVITY
    if _ACTIVITY is None:
        try:
            _ACTIVITY = json.loads(ACTIVITY_FILE.read_text())
        except Exception:
            _ACTIVITY = {}
    return _ACTIVITY


def activity_of(repo):
    """Weekly commit counts for the last 52 weeks, oldest first. GitHub computes these
    statistics lazily and answers 202 while it does; the last good value is kept so a
    slow answer never blanks a card."""
    cache = _load_activity()
    name = repo["name"]
    if repo.get("fork"):
        return []
    if name in _ACTIVITY_DONE:
        return cache.get(name, [])
    _ACTIVITY_DONE.add(name)
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"{API}/repos/{USER}/{name}/stats/commit_activity", headers=HEAD)
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    data = json.load(r)
                    if isinstance(data, list) and data:
                        weeks = [int(w.get("total", 0)) for w in data][-ACTIVITY_WEEKS:]
                        cache[name] = weeks
                        return weeks
        except Exception:
            pass
        if attempt < 2:
            time.sleep(2 * (attempt + 1))
    return cache.get(name, [])


def save_activity(repos):
    cache = _load_activity()
    keep = {r["name"] for r in repos}
    ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVITY_FILE.write_text(json.dumps({k: v for k, v in cache.items() if k in keep}, indent=0) + "\n")


CATEGORIES_FILE = ROOT / "docs" / "data" / "categories.json"
AUTO_FILE = ROOT / "docs" / "data" / "auto_meta.json"
MODELS_TOKEN = os.environ.get("MODELS_TOKEN", "")
RETRY_HOURS = 24


def understand_new_repos(repos):
    """Ask GitHub Models what each non-curated repo is, once per README version.
    Answers are cached; failures are retried after a day instead of on every run."""
    try:
        cache = json.loads(AUTO_FILE.read_text())
    except Exception:
        cache = {}
    now = datetime.now(timezone.utc)
    keep = {}
    for r in repos:
        name = r["name"]
        if r.get("fork") or name in portfolio.CURATED or portfolio.hidden(r, USER):
            continue
        readme = readme_of(r)
        sig = ai_classify.signature(r, readme)
        entry = cache.get(name) or {}
        fresh = entry.get("sig") == sig
        retry_ok = True
        if fresh and entry.get("answer") is None and entry.get("asked"):
            asked = datetime.fromisoformat(entry["asked"])
            retry_ok = (now - asked).total_seconds() > RETRY_HOURS * 3600
        if not fresh or (entry.get("answer") is None and retry_ok):
            answer = ai_classify.ask(r, readme, portfolio.category_menu(), MODELS_TOKEN)
            entry = {"sig": sig, "answer": answer, "asked": now.isoformat(timespec="seconds")}
            print(f"  read {name}: {answer['category'] + (' / ' + answer['new_category'] if answer and answer['new_category'] else '') if answer else 'no model answer, using rules'}")
        keep[name] = entry
        if entry.get("answer"):
            portfolio.AUTO[name] = entry["answer"]
    AUTO_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTO_FILE.write_text(json.dumps(keep, indent=1, ensure_ascii=False) + "\n")


def visible(repos):
    return [r for r in repos if not portfolio.hidden(r, USER)]


# ----------------------------------------------------------------- catalog

def _age_days(iso):
    if not iso:
        return 10 ** 6
    t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).days


def _month(iso):
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%b %Y")
    except (TypeError, ValueError):
        return ""


def _row(r):
    desc, stack = describe(r)
    name = f"**[{r['name']}]({r['html_url']})**"
    if _age_days(r.get("created_at")) <= NEW_DAYS:
        name += " <kbd>new</kbd>"
    stars = r.get("stargazers_count") or 0
    if stars:
        name += f" <sub>★ {stars}</sub>"
    desc = desc.replace("|", "\\|")
    return f"| {name} | {desc} | {stack} | {_month(r.get('pushed_at'))} |"


def _sort_key(r):
    return (-(r.get("stargazers_count") or 0), _age_days(r.get("pushed_at")))


def group_repos(repos):
    groups = {d: [] for d in DOMAIN_ORDER}
    for r in visible(repos):
        groups.setdefault(classify(r), []).append(r)
    for d in groups:
        groups[d].sort(key=_sort_key)
    return groups


def block_mindmap(groups):
    """Native GitHub Mermaid: renders inline, zoomable, no click needed."""
    def safe(t, n=30):
        t = re.sub(r"[()\[\]{}\"<>]", "", t).replace("&", "and")
        return t if len(t) <= n else t[:n - 1].rstrip("-_ ") + "…"

    total = sum(len(v) for v in groups.values())
    lines = ["```mermaid", "mindmap", f"  root((Akilan · {total} projects))"]
    for d in DOMAIN_ORDER:
        rs = groups.get(d) or []
        if not rs or d == "forks":
            continue
        lines.append(f"    {d}[{safe(CATALOG_LABELS[d], 60)} · {len(rs)}]")
        for r in rs[:4]:
            lines.append(f"      {safe(r['name'])}")
        if len(rs) > 4:
            lines.append(f"      +{len(rs) - 4} more")
    lines.append("```")
    return "\n".join(lines)


def _card_key(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


EXPLORER = f"https://{USER.lower()}.github.io/{USER}/repos.html"


def block_catalog(repos):
    """One animated card per repository, grouped by category. Every card links to its repo."""
    groups = group_repos(repos)
    cards = []
    out = ['<p align="center">' + pic("explore", "Open the interactive repository explorer: search, filter and flip every card",
                                      EXPLORER, "620", hashed=False) + "</p>", ""]
    visuals._LABELS.update(CATALOG_LABELS)
    for d in DOMAIN_ORDER:
        rs = groups.get(d) or []
        if not rs:
            continue
        out.append(f'<p align="center">{pic(f"section-{d}", f"{CATALOG_LABELS[d]}: {plural(len(rs), 'repo')}", f"{EXPLORER}#cat={d}", "100%", hashed=False)}</p>')
        out.append("")
        out.append('<p align="center">')
        for r in rs:
            desc, stack = describe(r)
            t = portfolio.title(r)
            for lead in (t, r["name"]):
                if desc.lower().startswith(lead.lower() + ":"):
                    desc = desc[len(lead) + 1:].strip()
                    desc = desc[:1].upper() + desc[1:]
            key = _card_key(r["name"])
            cards.append(dict(
                key=key, title=portfolio.title(r), slug=f"{USER}/{r['name']}", domain=d,
                desc=desc, stack=stack, stars=(r.get("stargazers_count") or 0) if (r.get("stargazers_count") or 0) > 1 else 0,
                updated=_month(r.get("pushed_at")), new=_age_days(r.get("created_at")) <= NEW_DAYS,
                fork=bool(r.get("fork")), activity=activity_of(r) if not r.get("fork") else []))
            out.append(pic(f"repo-{key}", f"{portfolio.title(r)}: {desc}", r["html_url"], "32%", hashed=False))
        out.append("</p>")
        out.append("")
    visuals.render_catalog(cards)
    # hash after the files exist so GitHub's image cache refreshes on change
    text = "\n".join(out)
    text = re.sub(r'assets/live/((?:repo-|section-|explore)[^"?]*?)-(dark|light)\.svg\?v=0',
                  lambda m: f'assets/live/{m.group(1)}-{m.group(2)}.svg?v={_ver(m.group(1))}', text)
    text += (f"\n<p align=\"center\"><sub>Every card opens its repository. Sorted automatically from each "
             f"repo's topics, description and README; new repositories appear here within six hours. "
             f"Recomputed {datetime.now(timezone.utc):%d %b %Y, %H:%M} UTC.</sub></p>")
    return text


def write_deck_data(repos, contrib):
    """Emit the JSON the Pages deck reads, so the 3D scenes track the live account."""
    data_dir = ROOT / "docs" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    nodes = []
    for r in visible(repos):
        stars = r.get("stargazers_count") or 0
        kb = r.get("size") or 0
        weight = 0.7 + min(2.4, (kb ** 0.5) / 26.0) + min(1.2, stars * 0.18)
        nodes.append({
            "name": r["name"],
            "domain": classify(r),
            "size": round(weight, 2),
            "stars": stars,
            "kb": kb,
            "lang": r.get("language") or "",
            "fork": bool(r.get("fork")),
            "pushed": (r.get("pushed_at") or "")[:10],
            "note": describe(r)[0],
            "url": r.get("html_url", ""),
            "title": portfolio.title(r),
            "stack": describe(r)[1],
            "created": (r.get("created_at") or "")[:10],
            "activity": activity_of(r),
        })
    nodes.sort(key=lambda n: -n["size"])
    used = {n["domain"] for n in nodes}
    domains = [{"key": k, "label": CATALOG_LABELS[k],
                "dark": visuals.domain_color(visuals.PAL["dark"], k),
                "light": visuals.domain_color(visuals.PAL["light"], k)}
               for k in DOMAIN_ORDER if k in used]
    (data_dir / "repos.json").write_text(json.dumps(
        {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "count": len(nodes), "domains": domains, "repos": nodes}, indent=1, ensure_ascii=False) + "\n")

    windows = contribution_windows()
    if windows:
        def summarise(label, c):
            days = []
            for wk in c["contributionCalendar"]["weeks"]:
                for d in wk["contributionDays"]:
                    days.append({"d": d["date"], "c": d["contributionCount"]})
            streak = best = 0
            for d in days:
                streak = streak + 1 if d["c"] > 0 else 0
                best = max(best, streak)
            busiest = max(days, key=lambda d: d["c"]) if days else {"d": "", "c": 0}
            return {
                "label": label,
                "total": c["contributionCalendar"]["totalContributions"],
                "commits": c.get("totalCommitContributions", 0),
                "prs": c.get("totalPullRequestContributions", 0),
                "issues": c.get("totalIssueContributions", 0),
                "reviews": c.get("totalPullRequestReviewContributions", 0),
                "longestStreak": best,
                "busiest": busiest,
                "days": days,
            }

        years = [summarise(label, c) for label, c in windows]
        payload = dict(years[0])
        payload["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["years"] = years
        (data_dir / "contributions.json").write_text(json.dumps(payload, indent=None) + "\n")
    print(f"  deck data written to docs/data/")


# ----------------------------------------------------------------- visual blocks

RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main"


def plain_blurb(r):
    return describe(r)[0]


def _ver(name):
    """Content hash in the URL so GitHub's image cache refreshes when a card changes."""
    f = visuals.LIVE / f"{name}-dark.svg"
    return hashlib.sha1(f.read_bytes()).hexdigest()[:8] if f.exists() else "0"


def pic(name, alt, href, width, hashed=True):
    v = _ver(name) if hashed else "0"
    alt = html.escape(alt, quote=True)
    return (f'<a href="{href}"><picture>'
            f'<source media="(prefers-color-scheme: dark)" srcset="{RAW}/assets/live/{name}-dark.svg?v={v}" />'
            f'<img src="{RAW}/assets/live/{name}-light.svg?v={v}" alt="{alt}" width="{width}" />'
            f'</picture></a>')


def latest_repos(repos, n=3):
    fresh = [r for r in visible(repos) if not r.get("fork")]
    fresh.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return fresh[:n]


def block_latest_visual(repos):
    rs = latest_repos(repos)
    if not rs:
        return "_No repositories yet._"
    return "<p align=\"center\">\n" + "\n".join(
        pic(f"latest-{i + 1}", f"New repository {r['name']}", r["html_url"], "32%")
        for i, r in enumerate(rs)) + "\n</p>"


def block_flagships():
    out = ["<p align=\"center\">"]
    for key, title, _ in showcase.FLAGSHIP_CARDS:
        out.append(pic(f"flag-{key}", f"{title}: flagship system", f"https://github.com/{USER}/{key}", "49%"))
    out.append("</p>")
    return "\n".join(out)


def block_city():
    return ("<p align=\"center\">\n"
            + pic("contrib-city", "A year of contributions as a 3D city of columns, with an activity radar and language mix",
                  f"https://github.com/{USER}", "100%") + "\n</p>")


def block_domains(groups):
    out = ["<p align=\"center\">"]
    for d in DOMAIN_ORDER:
        if groups[d]:
            out.append(pic(f"domain-{d}", f"{CATALOG_LABELS[d]}: {len(groups[d])} repositories",
                           "#-every-repository", "32%"))
    out.append("</p>")
    return "\n".join(out)


def block_ledger():
    return ("<p align=\"center\">\n"
            + pic("ledger", "Regression ledger: published versus fixed numbers",
                  f"https://github.com/{USER}/opendrivefm", "100%")
            + "\n</p>")


def block_header():
    return ("<p align=\"center\">\n"
            + pic("headline", "Camera-only BEV perception. Safety-critical autonomy. Agentic AI systems.",
                  DECK, "760") + "<br/>\n"
            + pic("stats", "Live account statistics", f"https://github.com/{USER}?tab=repositories", "620")
            + "\n</p>")


def block_drive():
    return ("<p align=\"center\">\n"
            + pic("drive", "Open the interactive perception deck: drive with W A S D", DECK, "560")
            + "\n</p>")


def block_pulse():
    return ("<p align=\"center\">\n"
            + pic("pulse", "Live GitHub telemetry", f"https://github.com/{USER}", "100%")
            + "\n</p>")


def _nice_ceiling(v):
    for step in (10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000):
        if v <= step:
            return step
    return v


def render_visuals(repos, contrib, stars, total, prs):
    groups = group_repos(repos)
    days = []
    if contrib:
        for wk in contrib["contributionCalendar"]["weeks"]:
            days += [{"d": d["date"], "c": d["contributionCount"]} for d in wk["contributionDays"]]
    else:
        try:
            days = json.loads((ROOT / "docs" / "data" / "contributions.json").read_text())["days"]
        except Exception:
            days = []
    n = len(repos)
    contribs = total if total is not None else sum(d["c"] for d in days)
    stats = [
        ("public repos", str(n), n / _nice_ceiling(n)),
        ("stars earned", str(stars), stars / _nice_ceiling(stars or 1)),
        ("contributions · 365d", f"{contribs:,}", contribs / _nice_ceiling(contribs or 1)),
        ("pull requests", str(prs["total"]), prs["total"] / _nice_ceiling(prs["total"] or 1)),
    ]
    visuals.render_all(groups, CATALOG_LABELS, latest_repos(repos), stats, days,
                       plain_blurb, classify)

    # 3D contribution city: drawn here from the same calendar, no third-party action
    try:
        cj = json.loads((ROOT / "docs" / "data" / "contributions.json").read_text())
    except Exception:
        cj = {}
    weights = {}
    for r in visible(repos):
        if r.get("fork"):
            continue
        lang = r.get("language") or "Other"
        weights[lang] = weights.get(lang, 0) + max(1, sum(activity_of(r)))
    total_w = sum(weights.values()) or 1
    ranked = sorted(((k, w) for k, w in weights.items() if k != "Other"), key=lambda kv: -kv[1])
    main = [(k, w) for k, w in ranked[:5] if w / total_w >= 0.01]
    rest = total_w - sum(w for _, w in main)
    langs = main + ([("Other", rest)] if rest > 0 else [])
    busiest = cj.get("busiest") or {}
    city_stats = dict(
        total=contribs, commits=cj.get("commits", 0), prs=cj.get("prs", prs["total"]),
        issues=cj.get("issues", 0), reviews=cj.get("reviews", 0),
        repos=len(visible(repos)), stars=stars, streak=cj.get("longestStreak", 0),
        busiest=f'{busiest.get("d", "")} · {busiest.get("c", 0)}' if busiest else "")
    for f in visuals.LIVE.glob("card-*.svg"):
        f.unlink()  # the old gauge cards, replaced by showcase.py
    showcase.render(days, langs, city_stats)
    return groups


def splice(text, marker, body):
    pat = re.compile(rf"(<!-- {marker}:START -->)(.*?)(<!-- {marker}:END -->)", re.S)
    if not pat.search(text):
        print(f"  ! marker {marker} not found, skipping", file=sys.stderr)
        return text
    return pat.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def main():
    user = get(f"{API}/users/{USER}")
    repos = all_repos()
    portfolio.load_registry(CATEGORIES_FILE)
    understand_new_repos(repos)
    contrib = contributions_last_year()
    prs = pull_requests()
    stars, total = write_endpoints(user, repos, contrib, prs)
    write_deck_data(repos, contrib)

    readme_path = ROOT / "README.md"
    text = readme_path.read_text()
    text = splice(text, "STATS", block_stats(user, repos, contrib, stars, total, prs))
    groups = render_visuals(repos, contrib, stars, total, prs)
    text = splice(text, "LATEST", block_latest_visual(repos))
    text = splice(text, "FLAGSHIPS", block_flagships())
    text = splice(text, "DOMAINS", block_domains(groups))
    text = splice(text, "PULSE", block_pulse())
    text = splice(text, "LEDGER", block_ledger())
    text = splice(text, "HEADER", block_header())
    text = splice(text, "DRIVE", block_drive())
    text = splice(text, "MINDMAP", block_mindmap(groups))
    text = splice(text, "CATALOG", block_catalog(repos))
    text = splice(text, "CITY", block_city())
    save_activity(visible(repos))
    portfolio.save_registry(CATEGORIES_FILE, {classify(r) for r in visible(repos)})
    readme_path.write_text(text)

    print(f"Updated README for {USER}: {len(repos)} repos, {stars} stars, "
          f"{prs['total']} PRs, {total} contributions.")


if __name__ == "__main__":
    main()
