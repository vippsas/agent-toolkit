# Vipps MobilePay plugin

Skills that let a coding agent add Vipps MobilePay to a system without guessing: which API to use, then how to
implement it, with the pitfalls and the go-live requirements that a checklist review will ask about.

One manifest per agent, one shared `skills/` folder, so Claude, Codex, and Cursor ship identical content.

## Skills

| Skill | Covers |
| ----- | ------ |
| `best-practices` | Entry point. Which API to use, platform basics, the rules that prevent broken integrations |
| `epayment` | One-time payments: web, app, in-store, QR, Express, capture, refund |
| `recurring` | Subscriptions and metered billing: agreements and charges |
| `login` | Identity, profile data, customer club sign-up |
| `webhooks` | Registration and HMAC verification, used by all of the above |
| `test-and-go-live` | Test environment, force approve, checklists |

```text
plugins/vipps/skills/
├── best-practices/SKILL.md
├── epayment/
│   ├── SKILL.md
│   └── references/    operations, features, errors
├── recurring/
│   ├── SKILL.md
│   └── references/    agreements, charges
├── login/
│   ├── SKILL.md
│   └── references/    browser-flow, merchant-initiated
├── webhooks/SKILL.md
└── test-and-go-live/SKILL.md
```

`best-practices` is the router. Its description is the broadest, so it is the one most likely to be matched from a
vague prompt, and it hands off to the specific skill from there.

## How it is meant to be read

An agent should need one skill for a task, not all six. So:

- The entry point answers "which API?" and states the facts every integration needs, then stops.
- Each API skill carries the shortest correct path through that API, the states to handle, and the traps.
- `references/` holds the long tables: every field, every error code, every optional feature. Loaded only when the task
  actually needs them.
- Anything not covered lives in the documentation. Every page at
  [developer.vippsmobilepay.com](https://developer.vippsmobilepay.com) is available as raw Markdown by appending `.md`
  to its path, and [`/llms.txt`](https://developer.vippsmobilepay.com/llms.txt) indexes all of them, so the skills point
  there rather than duplicating the whole documentation set.

## Keeping it honest

The skills restate facts from the developer documentation, which lives in another repository and changes without
touching this one. Nothing here is generated from it, so there is no copy to sync: what can go wrong is that a fact
stops being true. Three things guard against that.

**`sources.json`** declares which documentation pages each skill is derived from. It is a superset of the links written
inside the skills: a page belongs there if the skill asserts facts from it, whether or not it links to it. Add to it
whenever you take a fact from a new page.

**`scripts/check_sources.py`** verifies that every declared and cited page still resolves, and that no skill links to a
page it has not declared. Standard library only:

```bash
python scripts/check_sources.py            # includes the HTTP checks
python scripts/check_sources.py --offline   # declarations only
```

It runs on pull requests that touch `plugins/`, on push to `main`, and every Monday. The scheduled run is the one that
matters, since the documentation moves independently of this repository.

**The weekly accuracy review** (`.github/workflows/review-skill-accuracy.yml`) compares the numbers, enums, endpoints,
and error codes in each skill against the pages it declares. It opens a draft pull request when it finds a difference
and does nothing when it does not. It runs entirely in this repository and reaches into
`vippsas/vipps-developer-docs` read-only, so there is nothing to install or duplicate on that side.

Given read access to that repository it diffs `reviewed_commit` against `main`, reviews only the pages that changed, and
skips the model altogether when nothing did — which is what makes a weekly schedule cheap. Grant that access with
either a GitHub App (`APP_ID` and `APP_PRIVATE_KEY`, preferred: organization owned, short-lived tokens) or a
fine-grained token with `Contents: read` (`DOCS_REPO_TOKEN`).

With neither, it still works: it reads the published Markdown from the public documentation site. That path cannot
diff, so every declared page is in scope and each run costs more.

`reviewed_commit` only advances when a review opens a pull request. A run that finds nothing leaves it alone, so the
next run re-reads the same window. That is deliberate: it can waste tokens, but it can never skip a page. Bump it by
hand if you have confirmed a clean run.

Treat the output as a lead to verify, not as a fact. Read the cited page before merging anything it proposes.

## Maintaining it

When editing:

- Check the claim against the doc page before writing it. The API rejects invented field names, and a confidently wrong
  skill is worse than no skill.
- Keep the source of truth in the documentation. These files are a summary with judgment attached, not a second manual.
- Watch the things that differ between APIs and are easy to get backwards: ePayment amounts are
  `{ currency, value }` objects while Recurring amounts are plain integers; Login has its own OAuth token endpoint and
  does not use the Access Token API; Userinfo must not receive `Ocp-Apim-Subscription-Key`.
- Front matter descriptions are what a host matches against a user's prompt. They should name the concrete terms
  someone would actually type, including endpoint paths and error-adjacent words.
- A skill's `name` must match its directory name.
- Bump `version` in all three plugin manifests together, and keep the marketplace manifests at the repo root in step.
