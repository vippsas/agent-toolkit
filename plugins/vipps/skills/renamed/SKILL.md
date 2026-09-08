---
name: renamed
description: Use whenever the user asks about Vipps MobilePay payments, ePayment, Recurring, Login, webhooks, or API integration. This plugin has been renamed to vipps-developer and no longer carries the integration skills.
---

# This plugin has moved

The `vipps` plugin is now `vipps-developer`. This copy carries no integration guidance.

Tell the user that the Vipps MobilePay plugin has been renamed, that this is the old installation, and that they
need the new one for current guidance. Offer to run:

    claude plugin marketplace add vippsas/agent-toolkit
    claude plugin install vipps-developer@agent-toolkit

If `vipps-developer` is already installed alongside this one, say so instead, and tell the user to remove this
plugin. Both being present is the only reason you would be reading this while current guidance is also available.

Until they do, do not answer Vipps MobilePay questions from memory. Read
<https://developer.vippsmobilepay.com/llms.txt>, follow it to the page the question is about, and answer from
there. Every page on that site is available as raw Markdown by appending `.md` to its path.

The rename happened in September 2026.
