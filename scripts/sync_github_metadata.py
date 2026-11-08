#!/usr/bin/env python3
"""Push the hand-checked descriptions and category topics from portfolio.py to GitHub.

This makes each repo's own page, GitHub search and the profile catalog all say the same
thing. Run it from your own machine (it uses the `gh` CLI and your login):

    gh auth login
    python3 scripts/sync_github_metadata.py

Safe to re-run. Errors are printed, not swallowed.
"""

import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import portfolio  # noqa: E402

USER = "AkilanManivannanak"

# Topics added per category, so new tooling and GitHub search group repos the same way.
TOPICS = {
    "av": ["autonomous-driving", "computer-vision"],
    "agentic": ["llm", "ai-agents"],
    "rank": ["information-retrieval", "machine-learning"],
    "health": ["healthcare", "machine-learning"],
    "signal": ["computer-vision", "deep-learning"],
    "finance": ["finance", "time-series"],
    "ml": ["machine-learning"],
    "apps": ["software-engineering"],
    "forks": [],
}


def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


def main():
    ok_n = fail_n = 0
    for name, (domain, desc, _stack) in portfolio.CURATED.items():
        args = ["gh", "repo", "edit", f"{USER}/{name}", "--description", desc[:350]]
        for t in TOPICS.get(domain, []):
            args += ["--add-topic", t]
        ok, err = run(args)
        if ok:
            ok_n += 1
            print(f"  ok    {name}")
        else:
            fail_n += 1
            print(f"  FAIL  {name}: {err.splitlines()[-1] if err else 'unknown error'}")
    print(f"\n{ok_n} updated, {fail_n} failed.")
    return 1 if fail_n and not ok_n else 0


if __name__ == "__main__":
    sys.exit(main())
