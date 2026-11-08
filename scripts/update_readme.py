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


DOMAIN_LABELS = {
    "av": "Autonomous driving & BEV", "agentic": "Agentic AI · LLM · RAG",
    "rank": "Retrieval & ranking", "health": "Healthcare & biomedical",
    "signal": "Speech · vision · signal", "archive": "Coursework, forks, meta",
}


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


# Keyword rules for repos that are not hand-mapped above. A new repository lands in the
# right cluster on the next run as long as its name, description or topics say what it
# is. Topics are the most reliable signal, so they are weighted highest: tag a new repo
# with e.g. `autonomous-driving` or `rag` and it is categorised correctly first time.
RULES = {
    "av": ["bev", "birds-eye", "nuscenes", "waymo", "carla", "autonom", "self-driving",
           "selfdriving", "driving", "drive", "lidar", "occupancy", "trajectory", "adas",
           "vehicle", "traffic", "truck", "slam", "lane", "perception", "planning",
           "robot", "robotics", "nuplan", "kitti", "pointpillars", "bevformer"],
    "agentic": ["agent", "agents", "agentic", "llm", "llms", "rag", "langgraph", "langchain",
                "copilot", "gpt", "chatbot", "openai", "ollama", "prompt", "assistant",
                "genai", "generative", "claude", "anthropic", "mcp", "tutor", "automation"],
    "rank": ["recommend", "recommender", "recsys", "ranker", "ranking", "retrieval",
             "search", "faiss", "embedding", "embeddings", "als", "finder", "similarity",
             "vector", "bandit", "bandits", "ctr"],
    "health": ["health", "healthcare", "cancer", "disease", "medical", "clinical", "heart",
               "patient", "biobert", "biomedical", "alcohol", "diabetes", "ecg", "eeg",
               "radiology", "tumor", "covid", "drug"],
    "signal": ["speech", "audio", "kws", "keyword", "asl", "sign", "image", "images",
               "cnn", "vision", "webcam", "ocr", "gesture", "classification", "detection",
               "segmentation", "opencv", "yolo", "voice", "spectrogram"],
}
# Below this score a repo is treated as coursework / misc rather than guessed at.
MIN_SCORE = 2


def _tokens(text):
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text or "")
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def _score(tokens, words):
    hits = 0
    for w in words:
        if len(w) <= 4:
            hits += sum(1 for t in tokens if t == w)          # exact: rag, llm, bev, cnn
        else:
            hits += sum(1 for t in tokens if t.startswith(w))  # stem: autonom*, recommend*
    return hits


def classify(repo):
    name = repo["name"]
    if name in DOMAIN_MAP:
        return DOMAIN_MAP[name]
    name_t = _tokens(name)
    desc_t = _tokens(repo.get("description") or "")
    topic_t = _tokens(" ".join(repo.get("topics") or []))
    best, best_score = "archive", 0
    for domain, words in RULES.items():
        sc = 3 * _score(topic_t, words) + 2 * _score(name_t, words) + _score(desc_t, words)
        if sc > best_score:
            best, best_score = domain, sc
    return best if best_score >= MIN_SCORE else "archive"


# ----------------------------------------------------------------- catalog

DOMAIN_ORDER = ["av", "agentic", "rank", "health", "signal", "archive"]
DOMAIN_ICON = {"av": "🚗", "agentic": "🤖", "rank": "🔎", "health": "🩺",
               "signal": "🎙️", "archive": "🗂️"}
CATALOG_LABELS = dict(DOMAIN_LABELS, archive="Classical ML, coursework & forks")
NEW_DAYS = 30


def _humanise(name):
    return re.sub(r"[-_]+", " ", name).strip()


def _age_days(iso):
    if not iso:
        return 10 ** 6
    t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).days


def _blurb(r):
    text = NOTES.get(r["name"]) or (r.get("description") or "").strip()
    if not text:
        return "<sub><i>description pending</i></sub>"
    text = text.replace("|", "\\|")
    return text if len(text) <= 110 else text[:107].rstrip() + "…"


def _row(r):
    tags = []
    if _age_days(r.get("created_at")) <= NEW_DAYS:
        tags.append("![new](https://img.shields.io/badge/new-3fb8a6?style=flat-square)")
    if r.get("fork"):
        tags.append("<sub>fork</sub>")
    name = f"**[{r['name']}]({r['html_url']})**"
    if tags:
        name += " " + " ".join(tags)
    lang = f"`{r['language']}`" if r.get("language") else "–"
    stars = r.get("stargazers_count") or 0
    pushed = (r.get("pushed_at") or "")[:10]
    return f"| {name} | {_blurb(r)} | {lang} | {stars if stars else '·'} | {pushed} |"


def _sort_key(r):
    return (r.get("fork", False), -(r.get("stargazers_count") or 0), _age_days(r.get("pushed_at")))


def group_repos(repos):
    groups = {d: [] for d in DOMAIN_ORDER}
    for r in repos:
        if r["name"].lower() == USER.lower():
            continue  # this profile repo
        groups[classify(r)].append(r)
    for d in groups:
        groups[d].sort(key=_sort_key)
    return groups


def block_mindmap(groups):
    """Native GitHub Mermaid: renders inline, zoomable, no click needed."""
    def safe(t, n=30):
        t = re.sub(r"[()\[\]{}\"<>]", "", t).replace("&", "and")
        return t if len(t) <= n else t[:n - 1].rstrip("-_ ") + "…"

    lines = ["```mermaid", "mindmap", f"  root((Akilan · {sum(len(v) for v in groups.values())} repos))"]
    for d in DOMAIN_ORDER:
        rs = [r for r in groups[d] if not r.get("fork")]
        if not rs:
            continue
        lines.append(f"    {d}[{safe(CATALOG_LABELS[d], 60)} · {len(groups[d])}]")
        shown = rs[:4]
        for r in shown:
            lines.append(f"      {safe(r['name'])}")
        if len(groups[d]) > len(shown):
            lines.append(f"      +{len(groups[d]) - len(shown)} more")
    lines.append("```")
    return "\n".join(lines)


def block_latest(repos):
    fresh = [r for r in repos if not r.get("fork") and r["name"].lower() != USER.lower()]
    fresh.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    out = []
    for r in fresh[:3]:
        d = classify(r)
        out.append(f"- {DOMAIN_ICON[d]} **[{r['name']}]({r['html_url']})** "
                   f"<sub>· {CATALOG_LABELS[d]} · created {(r.get('created_at') or '')[:10]}</sub><br/>"
                   f"  {_blurb(r)}")
    return "\n".join(out) if out else "_No repositories yet._"


def block_catalog(repos):
    groups = group_repos(repos)
    out = ["<details>", "<summary><b>Full repository list</b> <sub>· every repo as a table, "
           "click to expand</sub></summary>", ""]
    for d in DOMAIN_ORDER:
        rs = groups[d]
        if not rs:
            continue
        # `open` keeps every category expanded by default: visible without a click,
        # still collapsible for anyone skimming.
        out.append(f"<details {'open' if d != 'archive' else ''}>")
        out.append(f"<summary><b>{DOMAIN_ICON[d]} {CATALOG_LABELS[d]}</b> "
                   f"<sub>· {plural(len(rs), 'repo')}</sub></summary>")
        out.append("")
        out.append("| Repository | What it is | Lang | ★ | Last push |")
        out.append("|---|---|---|---|---|")
        out += [_row(r) for r in rs]
        out.append("")
        out.append("</details>")
        out.append("")
    out.append("</details>")
    out.append("")
    out.append(f"<sub>Auto-sorted from repo topics, names and descriptions. "
               f"Repos created in the last {NEW_DAYS} days are tagged "
               f"<b>new</b>. Recomputed {datetime.now(timezone.utc):%d %b %Y, %H:%M} UTC.</sub>")
    return "\n".join(out)


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
        payload = dict(years[0])
        payload["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload["years"] = years
        (data_dir / "contributions.json").write_text(json.dumps(payload, indent=None) + "\n")
    print(f"  deck data written to docs/data/")


# ----------------------------------------------------------------- visual blocks

RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main"


def plain_blurb(r):
    return (NOTES.get(r["name"]) or (r.get("description") or "").strip())


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
    fresh = [r for r in repos if not r.get("fork") and r["name"].lower() != USER.lower()]
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
                           "#-repository-catalog", "32%"))
    out.append("</p>")
    return "\n".join(out)


def block_ledger():
    return ("<p align=\"center\">\n"
            + pic("ledger", "Regression ledger: published versus fixed numbers",
                  f"https://github.com/{USER}/opendrivefm", "100%")
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
    text = splice(text, "AUDIT", block_audit(repos, prs))
    groups = render_visuals(repos, contrib, stars, total, prs)
    text = splice(text, "LATEST", block_latest_visual(repos))
    text = splice(text, "FLAGSHIPS", block_flagships())
    text = splice(text, "DOMAINS", block_domains(groups))
    text = splice(text, "PULSE", block_pulse())
    text = splice(text, "LEDGER", block_ledger())
    text = splice(text, "MINDMAP", block_mindmap(groups))
    text = splice(text, "CATALOG", block_catalog(repos))
    readme_path.write_text(text)

    print(f"Updated README for {USER}: {len(repos)} repos, {stars} stars, "
          f"{prs['total']} PRs, {total} contributions.")


if __name__ == "__main__":
    main()
