# Security Policy

## Supported Versions

Only the latest release of Muninn is actively supported with security fixes.

| Version | Supported |
| ------- | --------- |
| Latest  | ✅        |
| Older   | ❌        |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability, open a [GitHub Security Advisory](https://github.com/antic-eye/muninn/security/advisories/new) on this repository. This keeps the report private until a fix is available.

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue
- Any relevant logs, error messages, or proof-of-concept code

You can expect an initial response within **7 days**. If the vulnerability is confirmed, a fix will be prioritised and a patched release will be published as soon as possible.

## Scope

Muninn is a local MCP server that stores memory in a ChromaDB database on your machine. It does not handle authentication, user accounts, or network-exposed services by default. The primary security concerns are:

- **Data directory permissions** — memory is stored at `~/.config/opencode/muninn/` (or `$MUNINN_DATA_DIR`). Ensure this path has appropriate filesystem permissions.
- **Embedding API credentials** — if you configure an external embedding endpoint via `MUNINN_EMBED_URL`, protect that credential as you would any API key.
- **MCP transport** — Muninn uses stdio transport by default. If you expose it over a network transport, apply appropriate access controls.
