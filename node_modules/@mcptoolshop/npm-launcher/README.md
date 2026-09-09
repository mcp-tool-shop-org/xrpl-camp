<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/npm-launcher/readme.png" width="400" alt="npm-launcher" />
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/npm-launcher/actions"><img src="https://github.com/mcp-tool-shop-org/npm-launcher/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://www.npmjs.com/package/@mcptoolshop/npm-launcher"><img src="https://img.shields.io/npm/v/@mcptoolshop/npm-launcher" alt="npm version"></a>
  <a href="https://github.com/mcp-tool-shop-org/npm-launcher/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
  <a href="https://mcp-tool-shop-org.github.io/npm-launcher/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

Generic GitHub-release binary launcher for npm. Downloads platform-specific binaries from GitHub Releases, caches them locally, verifies SHA256 checksums, and runs them with full arg passthrough.

Built so Python CLIs (or any compiled binary) get zero-dependency `npx` distribution.

## Security & Threat Model

npm-launcher downloads and executes binaries. Here's what it touches and what it doesn't:

- **Network:** HTTPS only, to `github.com` and GitHub's CDN. No other destinations.
- **Filesystem:** Writes to local cache only (`~/.cache/mcptoolshop/` or `%LOCALAPPDATA%\mcptoolshop\`). Does not modify system files or read outside the cache.
- **Verification:** Every binary is checked against SHA256 from a `checksums-<version>.txt` file in the same release. Mismatches abort execution and delete the downloaded file.
- **No telemetry.** No secrets handling. No credentials stored or transmitted.
- **Permissions:** None required beyond normal user filesystem access and outbound HTTPS.

## How It Works

```
npx @mcptoolshop/sovereignty tutorial
        │
        ▼
  wrapper sets config JSON
        │
        ▼
  npm-launcher resolves platform (linux-x64, darwin-arm64, etc.)
        │
        ▼
  checks local cache (~/.cache/mcptoolshop/<tool>/<version>/)
        │
        ├─ cached → run binary
        │
        └─ not cached:
             fetch checksums-<version>.txt from GitHub Release
             download <tool>-<version>-<os>-<arch>[.exe]
             verify SHA256
             cache + chmod +x
             run binary
```

## Install

```bash
npm install @mcptoolshop/npm-launcher
```

This package is a library for wrapper packages — end users install the wrapper (e.g. `npx @mcptoolshop/sovereignty`), not this directly.

## Config Contract

Wrappers pass pure JSON via `MCPTOOLSHOP_LAUNCH_CONFIG`. No functions, no magic.

| Field      | Required | Example                | Description                          |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | yes      | `"sovereignty"`        | Binary base name                     |
| `owner`    | yes      | `"mcp-tool-shop-org"`  | GitHub org/user                      |
| `repo`     | yes      | `"sovereignty"`        | GitHub repo name                     |
| `version`  | yes      | `"1.4.0"`              | Semver (no `v` prefix)               |
| `tag`      | no       | `"v1.4.0"`             | Git tag (defaults to `v<version>`)   |
| `quiet`    | no       | `true`                 | Suppress progress messages           |

## Asset Naming Convention

Locked. All tools follow the same pattern:

```
<toolName>-<version>-<os>-<arch><ext>
```

| Platform      | Example Asset                        |
|---------------|--------------------------------------|
| Linux x64     | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM     | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel   | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64   | `sovereignty-1.4.0-win-x64.exe`     |

Checksums file: `checksums-<version>.txt` (GNU coreutils format).

## Writing a Wrapper

A wrapper is a tiny npm package (~3 files):

**package.json:**
```json
{
  "name": "@mcptoolshop/sovereignty",
  "version": "1.4.0",
  "bin": { "sovereignty": "bin/sovereignty.js" },
  "dependencies": { "@mcptoolshop/npm-launcher": "^1.0.0" }
}
```

**bin/sovereignty.js:**
```js
#!/usr/bin/env node
process.env.MCPTOOLSHOP_LAUNCH_CONFIG = JSON.stringify({
  toolName: "sovereignty",
  owner: "mcp-tool-shop-org",
  repo: "sovereignty",
  version: "1.4.0",
});
require("@mcptoolshop/npm-launcher/bin/mcptoolshop-launch.js");
```

See `examples/sovereignty/` and `examples/xrpl-camp/` for complete wrapper templates, and `examples/ci/release-binaries.yml` for a PyInstaller CI workflow.

## Environment Variables

| Variable | Effect |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | Suppress progress messages (errors still print) |

## Supported Platforms

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## Cache Location

| OS      | Path                                         |
|---------|----------------------------------------------|
| Linux   | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS   | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

Built by <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a>
