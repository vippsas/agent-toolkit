<img src="plugins/vipps/assets/logo.svg" alt="Vipps MobilePay" width="64">

# Agent Toolkit for Vipps MobilePay

A plugin marketplace hosting installable agent plugins for Vipps MobilePay. The plugins give your coding agent up-to-date guidance for integrating one-time payments (ePayment API), recurring payments (Recurring API), and user login (Login API).

## Plugins

| Plugin | Description |
| --- | --- |
| [`vipps`](plugins/vipps) | Pick the right API, then implement it: payments, subscriptions, login, webhooks, and going live |

The `vipps` plugin ships one skill per goal, so an agent loads what the task needs instead of the whole documentation
set:

| Skill | Covers |
| --- | --- |
| `best-practices` | Entry point. Which API to use, platform basics, the rules that prevent broken integrations |
| `epayment` | One-time payments: web, app, in-store, QR, Express, capture, refund |
| `recurring` | Subscriptions and metered billing: agreements and charges |
| `login` | Identity, profile data, customer club sign-up |
| `webhooks` | Registration and HMAC verification, used by all of the above |
| `test-and-go-live` | Test environment, force approve, checklists |

## Installation

### Claude Code

```bash
claude plugin marketplace add vippsas/agent-toolkit
claude plugin install vipps@agent-toolkit
```

### Cursor

Add this repository as a plugin marketplace in Cursor, then install the `vipps` plugin. See the [Cursor plugin docs](https://cursor.com/docs).

### Codex

Add this repository as a plugin marketplace in Codex, then install the `vipps` plugin. See the [Codex plugin docs](https://developers.openai.com/codex).

## Repository layout

Marketplace manifests live at the repo root, one per agent ecosystem: `.claude-plugin/`, `.cursor-plugin/`, and `.agents/plugins/`. Each points at a plugin under `plugins/`.

A plugin directory holds one manifest per agent (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`) beside a single shared `skills/` folder, so every agent ships identical content.

## Documentation

Full API documentation lives at [developer.vippsmobilepay.com](https://developer.vippsmobilepay.com).

## License

[MIT](LICENSE)
