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


def contributions_last_year():
    """Rolling 365 days, matching the number GitHub itself renders."""
    if not TOKEN:
        return None
    to = datetime.now(timezone.utc)
    frm = to - timedelta(days=365)
    q = """
    query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from,to:$to){
          contributionCalendar{
            totalContributions
            weeks{ contributionDays{ date contributionCount } }
          }
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalPullRequestReviewContributions
        }
      }
    }"""
    data = gql(q, {"login": USER, "from": frm.isoformat(), "to": to.isoformat()})
    return data.get("data", {}).get("user", {}).get("contributionsCollection")


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

    if contrib:
        days = []
        for wk in contrib["contributionCalendar"]["weeks"]:
            for d in wk["contributionDays"]:
                days.append({"d": d["date"], "c": d["contributionCount"]})
        streak = best = 0
        for d in days:
            streak = streak + 1 if d["c"] > 0 else 0
            best = max(best, streak)
        busiest = max(days, key=lambda d: d["c"]) if days else {"d": "", "c": 0}
        (data_dir / "contributions.json").write_text(json.dumps({
            "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": contrib["contributionCalendar"]["totalContributions"],
            "commits": contrib.get("totalCommitContributions", 0),
            "prs": contrib.get("totalPullRequestContributions", 0),
            "issues": contrib.get("totalIssueContributions", 0),
            "reviews": contrib.get("totalPullRequestReviewContributions", 0),
            "longestStreak": best,
            "busiest": busiest,
            "days": days,
        }, indent=None) + "\n")
    print(f"  deck data written to docs/data/")


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
    readme_path.write_text(text)

    print(f"Updated README for {USER}: {len(repos)} repos, {stars} stars, "
          f"{prs['total']} PRs, {total} contributions.")


if __name__ == "__main__":
    main()
