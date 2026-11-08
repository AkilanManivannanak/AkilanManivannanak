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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import visuals  # noqa: E402
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


def get(url):
    req = urllib.request.Request(url, headers=HEAD)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GRAPHQL, data=body, headers={**HEAD, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


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
    data = gql(q, variables)
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
    except urllib.error.HTTPError:
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


def block_catalog(repos):
    groups = group_repos(repos)
    out = []
    for d in DOMAIN_ORDER:
        rs = groups.get(d) or []
        if not rs:
            continue
        out.append(f"#### {DOMAIN_ICON[d]} {CATALOG_LABELS[d]} <sub>· {plural(len(rs), 'repo')}</sub>")
        out.append("")
        out.append("| Repository | What it is | Built with | Updated |")
        out.append("|---|---|---|---|")
        out += [_row(r) for r in rs]
        out.append("")
    out.append(f"<sub>Sorted automatically from each repo's topics, description and README. "
               f"Repos created in the last {NEW_DAYS} days are tagged <b>new</b>. "
               f"Recomputed {datetime.now(timezone.utc):%d %b %Y, %H:%M} UTC.</sub>")
    return "\n".join(out)


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
        })
    nodes.sort(key=lambda n: -n["size"])
    (data_dir / "repos.json").write_text(json.dumps(
        {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "count": len(nodes), "repos": nodes}, indent=1) + "\n")

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


def pic(name, alt, href, width):
    v = _ver(name)
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
    for f in visuals.FLAGSHIPS:
        out.append(pic(f"card-{f['repo']}", f"{f['title']}: {f['metric']} {f['unit']}",
                       f"https://github.com/{USER}/{f['repo']}", "49%"))
    out.append("</p>")
    return "\n".join(out)


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
    readme_path.write_text(text)

    print(f"Updated README for {USER}: {len(repos)} repos, {stars} stars, "
          f"{prs['total']} PRs, {total} contributions.")


if __name__ == "__main__":
    main()
