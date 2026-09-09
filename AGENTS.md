# Repository instructions

This repository is a plugin marketplace. It hosts the installable Vipps MobilePay agent plugins: `vipps-developer`,
and `vipps`, which is deprecated and only tells an agent to install the new name.

## Always update the changelog

**Every change to a plugin needs an entry in that plugin's `CHANGELOG.md`, in the same commit as the change.**

- `plugins/vipps-developer/CHANGELOG.md`
- `plugins/vipps/CHANGELOG.md`

The version and its entry have to land together. A release whose entry is added later is a release nobody can read,
because the only other record is a commit titled with a timestamp.

How to write an entry:

- Newest release first, under a `## <version> - <YYYY-MM-DD>` heading.
- Say what changed for someone using the plugin, not which files moved. "The `description` field on a recurring
  charge is optional" is useful. "Updated psp/SKILL.md" is not.
- Bump the version in every manifest, so all three stay identical: `.claude-plugin/plugin.json`,
  `.codex-plugin/plugin.json`, and `.cursor-plugin/plugin.json`.
- A skills change is a minor bump. Keep the patch number at 0.

## The skills are generated

Everything under `plugins/*/skills/` is generated from the Vipps MobilePay developer documentation and copied in by an
automated workflow. **Do not edit a skill here** - the next sync overwrites it. If the user asks you to change one, tell
them what [Changing a skill](plugins/vipps-developer/README.md#changing-a-skill) says, and offer to make the same edit
in the documentation instead.

That workflow also writes the changelog entry for the release it creates, so an automated pull request already has
one. Check that it reads as a description of the change and improve it if it does not.

Everything else in the repository - the marketplace manifests, the READMEs, the plugin manifests - is edited here
by hand.

## Writing

- Use American English.
- Do not use `&`; write "and".
- Limit Markdown lines to 120 characters, and do not reflow lines you did not otherwise change.

## Pull requests

- Use plain, descriptive titles. Do not prefix them with a tool or agent name.
- Keep descriptions to a sentence or two on what changed and why.
- Open draft pull requests unless asked for one that is ready for review.
- This repository is public. Do not name the private repository the skills are generated from, and do not link to
  its issues or commits. A bare `#1234` also renders as a link to this repository's own issue of that number, which
  is worse than no reference at all.
