#!/usr/bin/env python3
"""Check that the vipps skills' documentation sources are still real.

Two failure modes this catches, both silent otherwise:

1. A documentation page the skills summarize was renamed, moved, or removed.
   The skill keeps asserting facts and citing a URL that now 404s.
2. plugins/vipps/sources.json drifted from the skills: a skill links to a page
   that is not declared, so the accuracy review never re-reads it.

Standard library only. Run it from the repository root:

    python scripts/check_sources.py
    python scripts/check_sources.py --offline   # skip HTTP, check declarations only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = REPO_ROOT / "plugins" / "vipps"
SOURCES = PLUGIN / "sources.json"
SKILLS = PLUGIN / "skills"

# Only the documentation site is checked. External sites (openid.net, Apple, Google,
# the brand portal) flake and would make this check noisy without telling us anything
# about whether a skill has gone stale.
URL_RE = re.compile(r"https://developer\.vippsmobilepay\.com/[a-zA-Z0-9._/-]*")

TIMEOUT = 20
USER_AGENT = "vipps-agent-toolkit-source-check"


def load_sources() -> dict:
    with SOURCES.open(encoding="utf-8") as handle:
        return json.load(handle)


def declared_urls(sources: dict) -> dict[str, set[str]]:
    """Map skill name to the absolute URLs it declares."""
    site = sources["site"].rstrip("/")
    out: dict[str, set[str]] = {}
    for skill, paths in sources["skills"].items():
        out[skill] = {site + path for path in paths}
    return out


def inline_urls() -> dict[str, set[str]]:
    """Map skill name to the documentation URLs written inside its files."""
    out: dict[str, set[str]] = {}
    for path in sorted(SKILLS.rglob("*.md")):
        skill = path.relative_to(SKILLS).parts[0]
        found = set(URL_RE.findall(path.read_text(encoding="utf-8")))
        out.setdefault(skill, set()).update(found)
    return out


def repo_paths(sources: dict) -> set[str]:
    """Convert declared site paths to paths in the documentation repository.

    The published `.md` is generated from `.mdx` at build time, so `/docs/x.md`
    on the site is `docs/x.mdx` in vippsas/vipps-developer-docs. `/llms.txt` is
    generated from the sidebar and has no source file, so it is skipped.
    """
    out = set()
    for paths in sources["skills"].values():
        for path in paths:
            if not path.endswith(".md"):
                continue
            out.add(path.lstrip("/")[: -len(".md")] + ".mdx")
    return out


def normalize(url: str) -> str:
    """A directory-style doc link and its raw Markdown file are the same page.

    `/docs/plugins/` is served as HTML, `/docs/plugins/README.md` is the raw file
    an agent reads. Treat them as one so a skill may link either form.
    """
    url = url.rstrip("/")
    if url.endswith("/README.md"):
        return url[: -len("/README.md")]
    if url.endswith(".md"):
        return url[: -len(".md")]
    return url


def check_declarations(sources: dict) -> list[str]:
    problems: list[str] = []
    declared = declared_urls(sources)
    inline = inline_urls()

    skill_dirs = {p.name for p in SKILLS.iterdir() if p.is_dir()}
    for skill in sorted(skill_dirs - set(declared)):
        problems.append(f"skill {skill!r} has no entry in sources.json")
    for skill in sorted(set(declared) - skill_dirs):
        problems.append(f"sources.json declares skill {skill!r}, which has no directory")

    index = sources["site"].rstrip("/") + sources["index"]
    for skill, urls in sorted(inline.items()):
        allowed = {normalize(u) for u in declared.get(skill, set())}
        allowed.add(normalize(index))
        for url in sorted(urls):
            if normalize(url) not in allowed:
                problems.append(f"{skill}: links {url} but does not declare it in sources.json")
    return problems


def fetch_status(url: str) -> tuple[str, int | str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return url, response.status
    except urllib.error.HTTPError as error:
        return url, error.code
    except Exception as error:  # noqa: BLE001 - network errors vary by platform
        return url, f"{type(error).__name__}: {error}"


def check_urls(sources: dict) -> list[str]:
    targets = set()
    for urls in declared_urls(sources).values():
        targets |= urls
    for urls in inline_urls().values():
        targets |= urls
    targets.add(sources["site"].rstrip("/") + sources["index"])

    problems: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for url, status in sorted(pool.map(fetch_status, sorted(targets))):
            if status != 200:
                problems.append(f"{status}  {url}")
    print(f"checked {len(targets)} documentation URLs")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="skip the HTTP checks")
    parser.add_argument(
        "--print-repo-paths",
        action="store_true",
        help="print the declared pages as paths in the documentation repository, one per line",
    )
    args = parser.parse_args()

    if args.print_repo_paths:
        for path in sorted(repo_paths(load_sources())):
            print(path)
        return 0

    problems = check_declarations(load_sources())
    if not args.offline:
        problems += check_urls(load_sources())

    if problems:
        print("\nProblems found:\n", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "\nA 404 means the page moved or was removed: find where the content went, "
            "update the skill and sources.json together.",
            file=sys.stderr,
        )
        return 1

    print("sources.json and every cited documentation URL check out")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
