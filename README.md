<img src="plugins/vipps/assets/logo.svg" alt="Vipps MobilePay" width="64">

# Agent Toolkit for Vipps MobilePay

A plugin marketplace hosting installable agent plugins for Vipps MobilePay. The plugins give your coding agent up-to-date guidance for integrating one-time payments (ePayment API), recurring payments (Recurring API), and user login (Login API).

## Plugins

| Plugin | Description |
| --- | --- |
| [`vipps`](plugins/vipps) | Payment integration guidance, best practices, and API help |

## Installation

### Claude Code

```bash
claude plugin marketplace add vippsas/agent-toolkit
claude plugin install vipps@agent-toolkit
```

### Cursor

Add this repository as a plugin marketplace in Cursor, then install the `vipps` plugin. See the [Cursor plugin docs](https://cursor.com/docs/plugins).

### Codex

Add this repository as a plugin marketplace in Codex, then install the `vipps` plugin. See the [Codex plugin docs](https://learn.chatgpt.com/docs/skills-and-plugins).

## Repository layout

Marketplace manifests live at the repo root, one per agent ecosystem: `.claude-plugin/`, `.cursor-plugin/`, and `.agents/plugins/`. Each points at a plugin under `plugins/`.

A plugin directory holds one manifest per agent (`.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`) beside a single shared `skills/` folder, so every agent ships identical content.

## Documentation

Full API documentation lives at [developer.vippsmobilepay.com](https://developer.vippsmobilepay.com).

## License

[MIT](LICENSE)
