#!/usr/bin/env python3
"""Reads a new repository's README and decides what it is, using GitHub Models.

Only repos that are not hand-curated in portfolio.py reach this. The answer is cached in
docs/data/auto_meta.json under a signature of the repo's description, topics and README, so
a repo is read once and re-read only when its README or description changes. If the model
is unavailable or answers badly, the caller falls back to keyword rules; nothing here can
break the build.
"""

import hashlib
import json
import os
import re
import urllib.request

ENDPOINT = "https://models.github.ai/inference/chat/completions"
MODEL = os.environ.get("CLASSIFY_MODEL", "openai/gpt-4.1-mini")


def signature(repo, readme):
    raw = "\n".join([repo.get("description") or "", ",".join(sorted(repo.get("topics") or [])),
                     (readme or "")[:12000]])
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:16]


def _prompt(repo, readme, domains):
    cats = "\n".join(f"- {k}: {label} ({scope})" for k, label, scope in domains)
    return f"""Categorise this GitHub repository for a portfolio page.

Existing categories (key: label (scope)):
{cats}

Repository
name: {repo["name"]}
language: {repo.get("language") or "unknown"}
GitHub description: {repo.get("description") or "none"}
topics: {", ".join(repo.get("topics") or []) or "none"}
README (may be truncated):
<<<
{(readme or "no README")[:7000]}
>>>

Answer with one JSON object and nothing else:
{{
  "category": "<one existing key, or \\"new\\" only if the project clearly belongs to a different field than every category above>",
  "new_category": "<2 to 4 word Title Case name of that field, only when category is new, else empty>",
  "confidence": <0.0 to 1.0>,
  "title": "<display name, at most 28 characters; use the product name if the README gives one>",
  "description": "<one sentence, at most 140 characters, saying what it does; use only facts and numbers that appear in the README or description; never invent metrics>",
  "stack": "<two or three key technologies named in the README, joined by ' · '>"
}}"""


def ask(repo, readme, domains, token):
    """domains: [(key, label, scope)]. Returns a validated dict or None."""
    if not token:
        return None
    body = json.dumps({
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 400,
        "messages": [
            {"role": "system", "content": "You are a precise technical librarian. Reply with JSON only."},
            {"role": "user", "content": _prompt(repo, readme, domains)},
        ],
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.load(r)
        text = data["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.S)
        out = json.loads(m.group(0)) if m else None
    except Exception as e:  # network, quota, model missing, bad JSON
        print(f"  ! model classification unavailable for {repo['name']}: {e}")
        return None
    return validate(out, [k for k, _, _ in domains])


def validate(out, keys):
    if not isinstance(out, dict):
        return None
    cat = str(out.get("category", "")).strip()
    try:
        conf = float(out.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    new = re.sub(r"\s+", " ", str(out.get("new_category") or "")).strip()[:40]
    if cat not in keys and cat != "new":
        return None
    if cat == "new" and (not new or conf < 0.55):
        return None
    if cat != "new" and conf < 0.35:
        return None

    def clean(s, n):
        s = re.sub(r"\s+", " ", str(s or "")).strip().strip('"')
        return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"
    return {
        "category": cat,
        "new_category": new if cat == "new" else "",
        "confidence": round(conf, 2),
        "title": clean(out.get("title"), 28),
        "description": clean(out.get("description"), 150),
        "stack": clean(out.get("stack"), 60),
    }
