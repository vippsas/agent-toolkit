# Vipps MobilePay plugin (renamed)

This plugin is now [`vipps-developer`](../vipps-developer). The name changed so it is not confused with the
third-party Vipps plugins that people also install.

## Installing the new one

The marketplace is already added, since this plugin came from it. Only the plugin itself needs installing.

### Claude Code

```bash
claude plugin install vipps-developer@agent-toolkit
```

### Cursor

Go to **Settings**, then **Plugins**, and install the `vipps-developer` plugin. See the
[Cursor plugin docs](https://cursor.com/docs).

### Codex

Install the `vipps-developer` plugin. See the [Codex plugin docs](https://developers.openai.com/codex).

## Why this directory is still here

It stays published on purpose. It holds a single skill that tells a coding agent the plugin has moved, so anyone
still on the old name finds out from their agent rather than from silence.
