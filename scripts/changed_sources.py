#!/usr/bin/env python3
"""Report which skills are affected by documentation changes.

Given a checkout of the documentation repository and the commit last reviewed,
this prints the declared source pages that changed since then and the skills
that summarize them. The accuracy review uses it to look at what moved instead
of re-reading every page.

    python scripts/changed_sources.py --docs-repo ../vipps-developer-docs
    python scripts/changed_sources.py --docs-repo ../vipps-developer-docs --base <sha>

With no `--base`, or a `--base` the checkout does not contain, it reports that
everything is in scope. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

from check_sources import SOURCES, load_sources


def git(repo: pathlib.Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def site_to_repo(path: str) -> str:
    return path.lstrip("/")[: -len(".md")] + ".mdx"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-repo", required=True, help="path to a checkout of the documentation repository")
    parser.add_argument("--base", default="", help="commit last reviewed; empty means review everything")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    args = parser.parse_args()

    repo = pathlib.Path(args.docs_repo).resolve()
    if not (repo / ".git").exists():
        print(f"{repo} is not a git checkout", file=sys.stderr)
        return 1

    sources = load_sources()
    head = git(repo, "rev-parse", "HEAD")

    # Which declared page belongs to which skills.
    owners: dict[str, list[str]] = {}
    for skill, paths in sources["skills"].items():
        for path in paths:
            if path.endswith(".md"):
                owners.setdefault(site_to_repo(path), []).append(skill)

    base = args.base.strip()
    have_base = bool(base)
    if have_base:
        try:
            git(repo, "cat-file", "-e", f"{base}^{{commit}}")
        except subprocess.CalledProcessError:
            have_base = False

    if not have_base:
        report = {
            "scope": "all",
            "head": head,
            "reason": "no usable reviewed_commit, so every declared page is in scope",
            "skills": sorted(sources["skills"]),
            "changed": [],
        }
    else:
        changed_all = git(repo, "diff", "--name-only", f"{base}..HEAD").splitlines()
        changed = sorted(set(changed_all) & set(owners))
        affected = sorted({skill for path in changed for skill in owners[path]})
        report = {
            "scope": "changed" if changed else "none",
            "head": head,
            "base": base,
            "reason": f"{len(changed)} declared page(s) changed between {base[:8]} and {head[:8]}",
            "skills": affected,
            "changed": [{"path": path, "skills": owners[path]} for path in changed],
        }

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print(f"Documentation repository HEAD: {report['head']}")
    print(f"Scope: {report['scope']} - {report['reason']}")
    if report["scope"] == "none":
        print("\nNothing to review. No declared source page changed.")
        return 0
    print(f"\nSkills in scope: {', '.join(report['skills'])}")
    if report["changed"]:
        print("\nChanged pages:")
        for entry in report["changed"]:
            print(f"  {entry['path']}  ->  {', '.join(entry['skills'])}")
    else:
        print(f"\nAll declared pages are in scope. See {SOURCES.name} for the list.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    raise SystemExit(main())
