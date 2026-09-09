<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

这是一个通用的 GitHub 发布二进制文件启动器，用于 npm。它从 GitHub 发布页面下载特定平台的二进制文件，将它们缓存在本地，验证 SHA256 校验和，并以完整参数传递的方式运行它们。

该工具旨在使 Python 命令行工具（或任何编译后的二进制文件）能够以零依赖的方式通过 `npx` 进行分发。

## 安全性和威胁模型

`npm-launcher` 下载并执行二进制文件。以下是它所涉及的内容以及它不涉及的内容：

- **网络：** 仅使用 HTTPS，连接到 `github.com` 和 GitHub 的 CDN。 不连接到其他目标地址。
- **文件系统：** 仅写入本地缓存目录 (`~/.cache/mcptoolshop/` 或 `%LOCALAPPDATA%\mcptoolshop\`)。 不修改系统文件，也不读取缓存目录以外的文件。
- **验证：** 每个二进制文件都与同一发布页面中的 `checksums-<version>.txt` 文件的 SHA256 值进行比较。 如果不匹配，则中止执行并删除下载的文件。
- **无遥测。** 不处理任何密钥。 不存储或传输任何凭据。
- **权限：** 仅需要正常的用户文件系统访问权限和出站 HTTPS 连接权限。

## 工作原理

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

## 安装

```bash
npm install @mcptoolshop/npm-launcher
```

此包是一个用于包装程序的库——最终用户安装包装程序（例如 `npx @mcptoolshop/sovereignty`），而不是直接安装此包。

## 配置接口

包装程序通过 `MCPTOOLSHOP_LAUNCH_CONFIG` 传递纯 JSON 数据。 不支持任何函数或魔法操作。

| 字段 | 是否必需 | 示例 | 描述 |
|------------|----------|------------------------|--------------------------------------|
| `toolName` | 是 | `"sovereignty"`        | 二进制文件基础名称 |
| `owner`    | 是 | `"mcp-tool-shop-org"`  | GitHub 组织/用户名 |
| `repo`     | 是 | `"sovereignty"`        | GitHub 仓库名称 |
| `version`  | 是 | `"1.4.0"`              | 语义版本号（不带 `v` 前缀） |
| `tag`      | no       | `"v1.4.0"`             | Git 标签（默认为 `v<version>`） |
| `quiet`    | no       | `true`                 | 抑制进度消息 |

## 资源命名约定

已锁定。 所有工具都遵循相同的模式：

```
<toolName>-<version>-<os>-<arch><ext>
```

| 平台 | 示例资源 |
|---------------|--------------------------------------|
| Linux x64 | `sovereignty-1.4.0-linux-x64`        |
| macOS ARM | `sovereignty-1.4.0-darwin-arm64`     |
| macOS Intel | `sovereignty-1.4.0-darwin-x64`       |
| Windows x64 | `sovereignty-1.4.0-win-x64.exe`     |

校验和文件：`checksums-<version>.txt` (GNU coreutils 格式)。

## 编写包装程序

一个包装程序是一个非常小的 npm 包（约 3 个文件）：

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

请参阅 `examples/` 目录，了解完整的包装程序模板和 CI 工作流程。

## 环境变量

| 变量 | 效果 |
|----------|--------|
| `MCPTOOLSHOP_LAUNCHER_QUIET=1` | 抑制进度消息（错误仍然会显示） |

## 支持的平台

- Linux x64
- macOS ARM64 (Apple Silicon)
- macOS x64 (Intel)
- Windows x64

## 缓存位置

| OS      | 路径 |
|---------|----------------------------------------------|
| Linux | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| macOS | `~/.cache/mcptoolshop/<tool>/<version>/`     |
| Windows | `%LOCALAPPDATA%\mcptoolshop\<tool>\<version>\` |

---

由 <a href="https://mcp-tool-shop.github.io/">MCP Tool Shop</a> 构建。
