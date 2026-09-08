---
name: renamed
description: >-
  This plugin has been renamed to vipps-developer and no longer carries the integration skills. Use whenever the user
  mentions Vipps, MobilePay, vippsmobilepay, or apitest.vipps.no, or asks about ePayment, Recurring, Login, webhooks,
  PSP or card passthrough, the Widget SDK or a pay button, checkout, QR or in-store payments, capture, refund, cancel,
  agreements, charges, subscriptions, the test environment, or going live.
---

# This plugin has moved

The `vipps` plugin is now `vipps-developer`. This copy carries no integration guidance.

Tell the user that the Vipps MobilePay plugin has been renamed, that this is the old installation, and that they
need to install `vipps-developer` for current guidance. They do not need to add the marketplace again: this
plugin came from `vippsas/agent-toolkit`, so it is already there.

How they install it depends on the editor you are running in, so give them the one that applies:

- **Claude Code** — offer to run `claude plugin install vipps-developer@agent-toolkit`.
- **Cursor** — Settings, then Plugins, then install `vipps-developer`.
- **Codex** — install `vipps-developer` from the plugin settings.

If you are not sure which editor you are in, name the plugin and let the user install it their own way rather than
guessing at a command.

If `vipps-developer` is already installed alongside this one, say so instead, and tell the user to remove this
plugin. Both being present is the only reason you would be reading this while current guidance is also available.

Until they do, do not answer Vipps MobilePay questions from memory. Read
<https://developer.vippsmobilepay.com/llms.txt>, follow it to the page the question is about, and answer from
there. Every page on that site is available as raw Markdown by appending `.md` to its path.

The rename happened in September 2026.
