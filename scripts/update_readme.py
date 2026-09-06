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

USER = os.environ.get("GH_USER", "AkilanManivannanak")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "output"

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


def block_activity(repos):
    recent = sorted((r for r in repos if r.get("pushed_at")),
                    key=lambda r: r["pushed_at"], reverse=True)[:6]
    lines = []
    for r in recent:
        when = datetime.strptime(r["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")
        desc = (r.get("description") or "").strip() or "no description set"
        lines.append(f"- **[{r['name']}]({r['html_url']})** · {when:%d %b %Y} · {desc}")
    return "\n".join(lines) if lines else "_No recent pushes._"


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def block_audit(repos, prs):
    findings = []

    missing = [r for r in repos if not (r.get("description") or "").strip() and not r.get("fork")]
    if missing:
        findings.append(f"- **{len(missing)} {'repository has' if len(missing) == 1 else 'repositories have'} "
                        f"no description.** Invisible to GitHub search. "
                        f"Worst offenders: {', '.join('`' + r['name'] + '`' for r in missing[:4])}.")

    empty = [r for r in repos if (r.get("size") or 0) < 2 and not r.get("fork")]
    if empty:
        findings.append(f"- **{len(empty)} {'repository is' if len(empty) == 1 else 'repositories are'} effectively empty**: "
                        f"{', '.join('`' + r['name'] + '`' for r in empty[:4])}.")

    nolicense = [r for r in repos if not r.get("license") and not r.get("fork")
                 and (r.get("stargazers_count") or 0) > 0]
    if nolicense:
        findings.append(f"- **{len(nolicense)} starred {'repository carries' if len(nolicense) == 1 else 'repositories carry'} no LICENSE**, "
                        f"so they read as all-rights-reserved: "
                        f"{', '.join('`' + r['name'] + '`' for r in nolicense[:3])}.")

    now = datetime.now(timezone.utc)
    for repo, num, title, created in prs["open_external"]:
        age = (now - datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).days
        findings.append(f"- **Upstream PR open {age} days**: "
                        f"[{repo}#{num}](https://github.com/{repo}/pull/{num}) — {title}")

    merged_external = [p for p in prs["external"] if p.get("state") == "closed"]
    findings.append(f"- **External pull requests: {len(prs['external'])} opened, "
                    f"{len(merged_external)} closed.** Landing merged code in an upstream "
                    f"AV repository is the current priority.")

    return "\n".join(findings) if findings else "_Nothing outstanding._"


# ----------------------------------------------------------------- isometric SVG

ISO_THEMES = {
    "dark":  {"bg":"#07090c", "rule":"#1d2a34", "txt":"#f2efe9", "mute":"#6f7b86",
              "levels":[("#141c23","#0f161c","#0c1218"),
                        ("#6b4a26","#553a1e","#3f2c16"),
                        ("#a06429","#7f4f21","#5f3b19"),
                        ("#e0873a","#b26b2e","#855022"),
                        ("#f5b877","#c4935f","#936e47")]},
    "light": {"bg":"#f5f3ef", "rule":"#ddd8ce", "txt":"#14171c", "mute":"#7d838b",
              "levels":[("#e6e2d9","#d8d4cb","#cac6bd"),
                        ("#e8c9a4","#cfb28f","#b69c7d"),
                        ("#d79a5a","#b98249","#9b6c3c"),
                        ("#b4531a","#933f13","#72300e"),
                        ("#8c3d10","#71300c","#562509")]},
}


def iso_contrib_svg(days, total, theme):
    """Isometric contribution surface, drawn from our own data. No third-party service."""
    t = ISO_THEMES[theme]
    hw, hh, unit = 7.4, 4.3, 1.05
    maxc = max([d["c"] for d in days] or [1]) or 1
    offset = datetime.strptime(days[0]["d"], "%Y-%m-%d").weekday()
    offset = (offset + 1) % 7  # Sunday-first, matching GitHub

    cells = []
    for idx, day in enumerate(days):
        n = idx + offset
        w, dow = divmod(n, 7)
        c = day["c"]
        lvl = 0 if c == 0 else min(4, 1 + int((c / maxc) * 3.999))
        h = 2.0 if c == 0 else 2.0 + (c / maxc) * 46 * unit
        cells.append((w, dow, h, lvl, day["d"], c))

    minx = min((w - d) * hw for w, d, _, _, _, _ in cells)
    maxx = max((w - d) * hw for w, d, _, _, _, _ in cells)
    maxy = max((w + d) * hh for w, d, _, _, _, _ in cells)
    maxh = max(h for _, _, h, _, _, _ in cells)
    padx, pady, top = 26, 58, 26
    W = int(maxx - minx + hw * 2 + padx * 2)
    H = int(maxy + hh * 2 + maxh + pady + top)
    ox = -minx + padx + hw
    oy = top + maxh

    body = []
    # painter's order: far cells first
    for w, d, h, lvl, date, c in sorted(cells, key=lambda x: (x[0] + x[1])):
        top_c, left_c, right_c = t["levels"][lvl]
        x = ox + (w - d) * hw
        y = oy + (w + d) * hh - h
        body.append(
            f'<g><title>{c} on {date}</title>'
            f'<path fill="{top_c}" d="M{x:.1f} {y:.1f}l{hw:.1f} {hh:.1f}l{-hw:.1f} {hh:.1f}l{-hw:.1f} {-hh:.1f}Z"/>'
            f'<path fill="{left_c}" d="M{x - hw:.1f} {y + hh:.1f}l{hw:.1f} {hh:.1f}v{h:.1f}l{-hw:.1f} {-hh:.1f}Z"/>'
            f'<path fill="{right_c}" d="M{x + hw:.1f} {y + hh:.1f}l{-hw:.1f} {hh:.1f}v{h:.1f}l{hw:.1f} {-hh:.1f}Z"/>'
            f'</g>')

    mono = 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace'
    head = (f'<text x="{padx}" y="30" fill="{t["txt"]}" '
            f'font-family="Archivo, Helvetica, Arial, sans-serif" font-weight="600" font-size="17">'
            f'{total:,} contributions</text>'
            f'<text x="{padx}" y="48" fill="{t["mute"]}" font-family="{mono}" font-size="10.5" '
            f'letter-spacing="1.4">{days[0]["d"]} — {days[-1]["d"]} · SELF-COMPUTED FROM THE GITHUB API</text>')
    foot = (f'<line x1="{padx}" y1="{H - 30}" x2="{W - padx}" y2="{H - 30}" stroke="{t["rule"]}"/>'
            f'<text x="{padx}" y="{H - 12}" fill="{t["mute"]}" font-family="{mono}" font-size="10" '
            f'letter-spacing="1.2">HOVER A COLUMN FOR THE DATE · FULL 3D VERSION IN THE PERCEPTION DECK</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'role="img" aria-label="Isometric view of {total} contributions over the last year.">'
            f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>{head}{"".join(body)}{foot}</svg>')


# ----------------------------------------------------------------- deck data

DOMAIN_MAP = {
    "opendrivefm": "av", "guardian-drive": "av", "autonomy-vision": "av",
    "Self-Driving-cars-Specialization": "av", "Traffic-Sense-Ideathon": "av",
    "nuscenes-devkit": "av", "Opendrivefm-1": "av", "vehicle-command": "av",
    "light-show": "av",
    "talentra_copilot": "agentic", "neurapilot": "agentic", "phamilyops": "agentic",
    "attentive-flow": "agentic", "stock-forecasting-aapl-LSTM-RAG": "agentic",
    "costsim-ai": "agentic",
    "two-stage-recommender-als-ranker-api": "rank", "FashionFinder": "rank",
    "Esophageal-Cancer-Detection": "health",
    "AI-Powered-Multi-Disease-Health-Risk-Prediction": "health",
    "Heart_disease_linear-regression": "health", "Alcohol_prediction": "health",
    "noise-robust-kws-distress-detection": "signal",
    "ASL-Alphabet-Recognition_A-Z_-Real-Time-Webcam-CNN": "signal",
    "Image-Classification-using-CNN": "signal",
}

NOTES = {
    "opendrivefm": "BEV occupancy + fault harness \u00b7 AUROC 0.764",
    "guardian-drive": "8 hazard detectors fused with BEV",
    "autonomy-vision": "SafeTruck-AV2 trucking stack \u00b7 ADE 18.78 m",
    "talentra_copilot": "5-agent hiring intelligence \u00b7 p95 4.81 ms",
    "neurapilot": "Agentic RAG tutor",
    "phamilyops": "17 AI modules, live deploy",
    "two-stage-recommender-als-ranker-api": "CineWave \u00b7 NDCG@10 0.1409",
    "FashionFinder": "44,419 items \u00b7 FAISS 1.79 ms",
    "noise-robust-kws-distress-detection": "77.02% at 0 dB SNR \u00b7 recall 0.02",
    "Esophageal-Cancer-Detection": "EfficientNet-B3 \u00b7 95.44%",
}


def classify(repo):
    name = repo["name"]
    if name in DOMAIN_MAP:
        return DOMAIN_MAP[name]
    if repo.get("fork"):
        return "av" if "drive" in name.lower() or "scenes" in name.lower() else "archive"
    return "archive"


def write_deck_data(repos, contrib):
    """Emit the JSON the Pages deck reads, so the 3D scenes track the live account."""
    data_dir = ROOT / "docs" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    nodes = []
    for r in repos:
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
            "note": NOTES.get(r["name"]) or (r.get("description") or "").strip()
                    or ("fork" if r.get("fork") else "no description set"),
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
        assets = ROOT / "assets"
        assets.mkdir(exist_ok=True)
        for theme in ("dark", "light"):
            (assets / f"contrib-iso-{theme}.svg").write_text(
                iso_contrib_svg(years[0]["days"], years[0]["total"], theme))
        payload = dict(years[0])
        payload["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["years"] = years
        (data_dir / "contributions.json").write_text(json.dumps(payload, indent=None) + "\n")
    print(f"  deck data written to docs/data/")


def block_contrib_graph(has_data):
    if not has_data:
        return ("_Generated once the workflow runs with `PROFILE_TOKEN` set: the contributions "
                "calendar is only readable through authenticated GraphQL._")
    base = f"https://raw.githubusercontent.com/{USER}/{USER}/main/assets"
    return ('<picture>\n'
            f'  <source media="(prefers-color-scheme: dark)" srcset="{base}/contrib-iso-dark.svg" />\n'
            f'  <img src="{base}/contrib-iso-light.svg" alt="Isometric view of the last year of contributions" width="100%" />\n'
            '</picture>')


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
    text = splice(text, "ACTIVITY", block_activity(repos))
    text = splice(text, "AUDIT", block_audit(repos, prs))
    text = splice(text, "CONTRIBGRAPH",
                  block_contrib_graph((ROOT / "assets" / "contrib-iso-dark.svg").exists()))
    readme_path.write_text(text)

    print(f"Updated README for {USER}: {len(repos)} repos, {stars} stars, "
          f"{prs['total']} PRs, {total} contributions.")


if __name__ == "__main__":
    main()
