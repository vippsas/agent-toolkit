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

## Maintaining it

The skills restate facts from the developer documentation, so they go stale when the APIs change. When editing:

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
